#!/usr/bin/env python3
"""
Interpreta mensagens WhatsApp de saída de estoque (defensivos, adubos, lubrificantes).

Exemplo:
  Anderson Correia
  20L Agefix
  120L ZAPP
  Horto Sede - Pasto 430

Uso standalone:
  python interpretar_mensagem.py
  python interpretar_mensagem.py "texto..."
  python interpretar_mensagem.py --arquivo mensagem.txt
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


UNIDADES = {"L", "LT", "KG", "ML", "FR", "UN", "SC", "CX", "GL"}

UN_PATTERN = (
    r"(?:lts|litros|litro|lt|l|kgs|quilos|quilo|kg|g|ml|mls|"
    r"fr|frs|frasco|un|und|unid|unidade|sc|cx|gl)\.?"
)

ITEM_QTD_PRIMEIRO = re.compile(
    rf"^\s*(\d+(?:[.,]\d+)?)\s*({UN_PATTERN})\s*(?:de\s+)?(.+?)\s*$",
    re.IGNORECASE,
)
ITEM_PROD_PRIMEIRO = re.compile(
    rf"^\s*(?:de\s+)?(.+?)\s+(\d+(?:[.,]\d+)?)\s*({UN_PATTERN})\s*$",
    re.IGNORECASE,
)
# Medicamentos campo: "3 umbicura", "4 borgal", "1 Topline" (sem unidade)
ITEM_QTD_PROD = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s+(.+?)\s*$",
    re.IGNORECASE,
)
ITEM_SERINGA = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s+[Ss]eringas?(?:\s+de)?\s*(\d+(?:[.,]\d+)?)\s*ml\s*$",
    re.IGNORECASE,
)
ITEM_AGULHA = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s+[Aa]gulhas?(?:\s+(?:desc\.?\s+)?40\s*[xX]\s*12|\s+40x12)?\s*$",
    re.IGNORECASE,
)
PASTO_RE = re.compile(r"(?:pasto|p\.?)\s*(\d+)", re.IGNORECASE)
TALHAO_RE = re.compile(r"(?:talh[aã]o|tal\.?)\s*(\d+)", re.IGNORECASE)

DESTINO_KW = (
    "pasto", "talhao", "talhão", "horto", "retiro", "sede", "aldeia",
    "viveiro", "torre", "estrada", "setor", "depósito", "deposito",
)

NOME_RE = re.compile(r"^[A-Za-zÀ-ÿ\s\-']{4,80}$")

PRODUTO_ALIASES: dict[str, list[str]] = {
    "AGEFIX": ["agefix", "age fix", "oleo agefix"],
    "ZAPP": ["zapp", "z app"],
    "ROUNDUP": ["roundup", "round up"],
    "GLIFOS": ["glifos", "glifosato", "glyphos"],
    "CRUCIAL": ["crucial"],
    "FORDOR": ["fordor"],
    "ISAC FORMICIDA": ["landrin", "isca formicida", "formicida 25", "formicida 25kg"],
    "ATADURA": ["atadura", "tala gessada", "tala", "gesso"],
    # Medicamentos — apelidos de campo
    "UMBICURA": ["umbicura"],
    "PRATA": ["prata", "spray prata", "silverbac", "silver bac"],
    "TOPLINE": ["topline", "top line"],
    "BORGAL": ["borgal"],
    "MAXICAM": ["maxicam", "maxican"],
    "TERRACORTRIL": ["terra-cortril", "terracortril", "terra cortril"],
    "AGROVET": ["agrovet"],
    "CALFON": ["calfon"],
    "RINGER": ["ringer"],
    "UNGENTO": ["unguento"],
    "EQUIPO": ["equipo"],
    "TERRAMICINA": ["terramicina"],
    "DESFLAN": ["desflan"],
    "MONOVIN K": ["monovin k"],
    "MONOVIN B1": ["monovin b1", "monovin b 1"],
    "MONOVIN B12": ["monovin b12", "monovin b 12"],
    "MONOVIN A": ["monovin a", "monovin - a"],
    "MERCEPTON": ["mercepton"],
    "ISACORT": ["isacort"],
    "SORO": ["soro"],
    "SERINGA 10ML": ["seringa 10", "seringa 10ml"],
    "SERINGA 20ML": ["seringa 20", "seringa 20ml"],
    "AGULHA 40X12": ["agulha 40x12", "agulha 40 x12"],
}

# Apelido campo → código SAP (ordem: frases mais longas primeiro em codigo_por_apelido)
ALIAS_CODIGO_SAP: dict[str, str] = {
    "LANDRIN": "02459",
    "ISCA FORMICIDA": "02459",
    "FORMICIDA 25": "02459",
    "TALA GESSADA": "02058",
    "ATADURA DE GESSO": "02058",
    "ATADURA": "02058",
    "PRATA": "01094",
    "SPRAY PRATA": "01094",
    "SILVERBAC": "01094",
    "SILVERBAC PRATA": "01094",
    "UMBICURA": "00536",
    "TOPLINE": "01864",
    "TOP LINE": "01864",
    "BORGAL": "00463",
    "MAXICAM": "02101",
    "MAXICAN": "02101",
    "TERRACORTRIL": "01102",
    "TERRA-CORTRIL": "01102",
    "AGROVET": "00447",
    "CALFON": "01961",
    "RINGER": "00511",
    "UNGENTO": "00466",
    "EQUIPO": "00482",
    "TERRAMICINA": "01578",
    "DESFLAN": "00478",
    "MONOVIN B 12": "00506",
    "MONOVIN B12": "00506",
    "MONOVIN B 1": "00505",
    "MONOVIN B1": "00505",
    "MONOVIN K": "00504",
    "MONOVIN A": "01095",
    "MERCEPTON": "00503",
    "ISACORT": "02143",
    "SORO ANTITETANICO": "00527",
    "SORO": "00527",
    "SERINGA 20ML": "00516",
    "SERINGA 10ML": "00514",
    "AGULHA 40X12": "00449",
    "AGULHA 40 X12": "00449",
}

# Fallback se catálogo Supabase ainda não tiver o item
CATALOGO_FALLBACK: dict[str, dict] = {
    "00504": {"codigo_sap": "00504", "descricao_sap": "MONOVIN K 20ML", "descricao_resumida": "Monovin K", "ativo": True},
    "00505": {"codigo_sap": "00505", "descricao_sap": "MONOVIN B 1 - 20ml", "descricao_resumida": "Monovin B1", "ativo": True},
}


def codigo_por_apelido(busca: str) -> str | None:
    """Resolve apelido de campo → código SAP (regras específicas antes do genérico)."""
    b = norm_txt(busca)
    if "MONOVIN" in b:
        if " B 12" in b or " B12" in b:
            return "00506"
        if " K" in b or b.endswith(" K"):
            return "00504"
        if " B1" in b or " B 1" in b:
            return "00505"
        if " A" in b or " - A" in b:
            return "01095"
    if "SERINGA" in b and "20" in b:
        return "00516"
    if "SERINGA" in b and "10" in b:
        return "00514"
    for alias, codigo in sorted(ALIAS_CODIGO_SAP.items(), key=lambda x: len(x[0]), reverse=True):
        if alias in b:
            return codigo
    return None


def produto_catalogo(codigo: str, catalogo: list[dict]) -> dict | None:
    for p in catalogo:
        if p.get("codigo_sap") == codigo and p.get("ativo", True):
            return p
    return CATALOGO_FALLBACK.get(codigo)


@dataclass
class MatchResult:
    valor: Any = None
    confianca: float = 0.0
    detalhe: str = ""


@dataclass
class ItemInterpretado:
    texto_linha: str
    produto_texto: str
    quantidade: float
    unidade: str
    produto_match: MatchResult = field(default_factory=MatchResult)
    ordem: int = 1


@dataclass
class SaidaInterpretada:
    texto_original: str
    responsavel: MatchResult = field(default_factory=MatchResult)
    destino_texto: str | None = None
    local: MatchResult = field(default_factory=MatchResult)
    talhao: MatchResult = field(default_factory=MatchResult)
    itens: list[ItemInterpretado] = field(default_factory=list)
    linhas_nao_reconhecidas: list[str] = field(default_factory=list)

    @property
    def confianca_media(self) -> float:
        scores = [i.produto_match.confianca for i in self.itens if i.produto_match.confianca]
        if self.local.confianca:
            scores.append(self.local.confianca)
        if self.talhao.confianca:
            scores.append(self.talhao.confianca)
        return round(sum(scores) / len(scores), 3) if scores else 0.0


def norm_txt(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.strip().upper())


def norm_unidade(u: str) -> str:
    u = u.strip().upper().replace(".", "")
    if u in ("L", "LT", "LTS", "LITRO", "LITROS"):
        return "LT"
    if u in ("KGS", "QUILO", "QUILOS", "G"):
        return "KG"
    if u in ("MILILITRO", "MILILITROS", "MLS"):
        return "ML"
    if u in ("FRASCO", "FRS"):
        return "FR"
    if u in ("UNID", "UNIDADE", "UNIDADES", "UND"):
        return "UN"
    return u


def limpar_produto(nome: str) -> str:
    return re.sub(r"^(?:de\s+)", "", nome.strip(), flags=re.IGNORECASE)


def parse_quantidade(raw: str) -> float:
    return float(raw.replace(",", "."))


def linha_ignoravel(linha: str) -> bool:
    t = linha.strip()
    return not t or bool(re.match(r"^[\s\.·…\-_=]+$", t))


def parece_nome(linha: str) -> bool:
    t = linha.strip()
    if not t or any(c.isdigit() for c in t):
        return False
    if parse_linha_item(t):
        return False
    low = t.lower()
    if any(k in low for k in DESTINO_KW):
        return False
    if "-" in t and len(t.split()) >= 2:
        return False
    if not NOME_RE.match(t):
        return False
    palavras = [p for p in re.split(r"\s+", t) if len(p) > 1]
    # Ramon, Sidnei (nome único)
    if len(palavras) == 1:
        return True
    return len(palavras) >= 2


def parece_destino(linha: str) -> bool:
    low = linha.lower()
    return any(k in low for k in DESTINO_KW) or bool(PASTO_RE.search(linha)) or bool(TALHAO_RE.search(linha))


def parse_linha_item(linha: str) -> tuple[float, str, str] | None:
    t = linha.strip()
    m = ITEM_SERINGA.match(t)
    if m:
        ml = m.group(2).replace(",", ".")
        if ml.endswith(".0"):
            ml = ml[:-2]
        return parse_quantidade(m.group(1)), "UN", f"Seringa {ml}ml"
    m = ITEM_AGULHA.match(t)
    if m:
        return parse_quantidade(m.group(1)), "UN", "Agulha 40x12"
    m = ITEM_QTD_PRIMEIRO.match(t)
    if m:
        return parse_quantidade(m.group(1)), norm_unidade(m.group(2)), limpar_produto(m.group(3))
    m = ITEM_PROD_PRIMEIRO.match(t)
    if m:
        return parse_quantidade(m.group(2)), norm_unidade(m.group(3)), limpar_produto(m.group(1))
    m = ITEM_QTD_PROD.match(t)
    if m:
        prod = limpar_produto(m.group(2))
        if parece_destino(prod):
            return None
        return parse_quantidade(m.group(1)), "UN", prod
    return None


def score_strings(a: str, b: str) -> float:
    na, nb = norm_txt(a), norm_txt(b)
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.92
    ratio = SequenceMatcher(None, na, nb).ratio()
    tokens_a = set(na.split())
    tokens_b = set(nb.split())
    if tokens_a and tokens_b:
        overlap = len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))
        ratio = max(ratio, overlap * 0.95)
    return round(ratio, 3)


def match_produto(nome: str, catalogo: list[dict]) -> MatchResult:
    if not nome or not catalogo:
        return MatchResult(detalhe="Catálogo vazio")

    busca = norm_txt(nome)

    for alias_key, terms in PRODUTO_ALIASES.items():
        if any(t in busca for t in [norm_txt(x) for x in terms + [alias_key.lower()]]):
            busca = f"{busca} {alias_key}"

    codigo = codigo_por_apelido(busca) or codigo_por_apelido(nome)
    if codigo:
        prod = produto_catalogo(codigo, catalogo)
        if prod:
            label = prod.get("descricao_sap") or prod.get("descricao_resumida", "")
            return MatchResult(
                valor=prod,
                confianca=0.95,
                detalhe=f"{codigo} — {label}",
            )

    melhor: dict | None = None
    melhor_score = 0.0

    for p in catalogo:
        if not p.get("ativo", True):
            continue
        candidatos = [
            p.get("descricao_resumida") or "",
            p.get("descricao_sap") or "",
            p.get("codigo_sap") or "",
        ]
        for cand in candidatos:
            sc = max(score_strings(nome, cand), score_strings(busca, cand))
            if sc > melhor_score:
                melhor_score = sc
                melhor = p

    if melhor and melhor_score >= 0.45:
        cod = melhor.get("codigo_sap", "")
        label = melhor.get("descricao_sap") or melhor.get("descricao_resumida", "")
        return MatchResult(
            valor=melhor,
            confianca=melhor_score,
            detalhe=f"{cod} — {label}",
        )
    return MatchResult(detalhe=f"Sem match para '{nome}' (melhor={melhor_score:.2f})")


def match_local(destino: str, locais: list[dict]) -> MatchResult:
    if not destino or not locais:
        return MatchResult()
    texto = norm_txt(destino.replace("-", " "))
    melhor: dict | None = None
    melhor_score = 0.0
    for loc in locais:
        if not loc.get("ativo", True):
            continue
        nome = norm_txt(loc.get("nome") or "")
        sc = score_strings(texto, nome)
        if nome and nome in texto:
            sc = max(sc, 0.88)
        for parte in texto.split():
            if len(parte) >= 4 and parte in nome:
                sc = max(sc, 0.75)
        if sc > melhor_score:
            melhor_score = sc
            melhor = loc
    if melhor and melhor_score >= 0.55:
        return MatchResult(valor=melhor, confianca=melhor_score, detalhe=melhor.get("nome", ""))
    return MatchResult(detalhe=f"Local não identificado (melhor={melhor_score:.2f})")


def match_talhao(destino: str, talhoes: list[dict]) -> MatchResult:
    if not destino:
        return MatchResult()
    m = PASTO_RE.search(destino) or TALHAO_RE.search(destino)
    if not m:
        return MatchResult()
    codigo = m.group(1)
    for t in talhoes:
        if not t.get("ativo", True):
            continue
        tc = str(t.get("codigo") or "").strip()
        if tc == codigo:
            return MatchResult(valor=t, confianca=0.98, detalhe=t.get("nome") or f"Pasto {codigo}")
    return MatchResult(
        valor={"codigo": codigo, "nome": f"PASTO {codigo}"},
        confianca=0.7,
        detalhe=f"Pasto {codigo} (não cadastrado em dim_talhoes)",
    )


def interpretar_mensagem(
    texto: str,
    catalogo: list[dict] | None = None,
    locais: list[dict] | None = None,
    talhoes: list[dict] | None = None,
) -> SaidaInterpretada:
    catalogo = catalogo or []
    locais = locais or []
    talhoes = talhoes or []

    linhas = [ln.strip() for ln in texto.strip().splitlines() if ln.strip()]
    saida = SaidaInterpretada(texto_original=texto.strip())

    idx = 0
    if linhas and parece_nome(linhas[0]):
        saida.responsavel = MatchResult(valor=linhas[0].strip(), confianca=0.85, detalhe=linhas[0].strip())
        idx = 1

    destino_linhas: list[str] = []
    itens_raw: list[tuple[str, float, str, str]] = []

    for ln in linhas[idx:]:
        if linha_ignoravel(ln):
            continue
        if parece_destino(ln) and not parse_linha_item(ln):
            destino_linhas.append(ln)
            continue
        parsed = parse_linha_item(ln)
        if parsed:
            qtd, un, prod = parsed
            itens_raw.append((ln, qtd, un, prod))
        else:
            saida.linhas_nao_reconhecidas.append(ln)

    if destino_linhas:
        saida.destino_texto = " — ".join(destino_linhas)
    elif saida.linhas_nao_reconhecidas:
        candidato = saida.linhas_nao_reconhecidas[-1]
        if parece_destino(candidato):
            saida.destino_texto = candidato
            saida.linhas_nao_reconhecidas = saida.linhas_nao_reconhecidas[:-1]

    for i, (ln, qtd, un, prod) in enumerate(itens_raw, start=1):
        match = match_produto(prod, catalogo)
        saida.itens.append(
            ItemInterpretado(
                texto_linha=ln,
                produto_texto=prod,
                quantidade=qtd,
                unidade=un,
                produto_match=match,
                ordem=i,
            )
        )

    if saida.destino_texto:
        saida.local = match_local(saida.destino_texto, locais)
        saida.talhao = match_talhao(saida.destino_texto, talhoes)

    return saida


def resumo_dict(s: SaidaInterpretada) -> dict:
    return {
        "responsavel": s.responsavel.valor,
        "destino": s.destino_texto,
        "local": s.local.detalhe or None,
        "talhao": s.talhao.detalhe or None,
        "confianca_media": s.confianca_media,
        "itens": [
            {
                "linha": it.texto_linha,
                "produto": it.produto_texto,
                "quantidade": it.quantidade,
                "unidade": it.unidade,
                "sap": (it.produto_match.valor or {}).get("codigo_sap") if it.produto_match.valor else None,
                "match": it.produto_match.detalhe,
                "confianca": it.produto_match.confianca,
            }
            for it in s.itens
        ],
        "nao_reconhecidas": s.linhas_nao_reconhecidas,
    }


def main():
    parser = argparse.ArgumentParser(description="Interpreta mensagem WhatsApp de saída de estoque")
    parser.add_argument("texto", nargs="?", help="Texto da mensagem")
    parser.add_argument("--arquivo", "-f", help="Arquivo .txt com a mensagem")
    args = parser.parse_args()

    if args.arquivo:
        texto = Path(args.arquivo).read_text(encoding="utf-8")
    elif args.texto:
        texto = args.texto
    else:
        texto = """Anderson Correia
20L Agefix
120L ZAPP
Horto Sede - Pasto 430"""

    catalogo_demo = [
        {"codigo_sap": "01234", "descricao_resumida": "Agefix", "descricao_sap": "AGEFIX OLEO 20L", "ativo": True},
        {"codigo_sap": "05678", "descricao_resumida": "Zapp", "descricao_sap": "ZAPP HERBICIDA", "ativo": True},
    ]
    locais_demo = [{"id": 9, "nome": "HORTO SEDE", "ativo": True}, {"id": 7, "nome": "SEDE", "ativo": True}]
    talhoes_demo = [{"id": 1, "codigo": "430", "nome": "PASTO 430", "ativo": True}]

    r = interpretar_mensagem(texto, catalogo_demo, locais_demo, talhoes_demo)
    print(json.dumps(resumo_dict(r), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
