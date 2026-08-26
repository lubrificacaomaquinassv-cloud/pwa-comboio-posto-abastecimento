#!/usr/bin/env python3
"""Importa NF-e XML -> preco_compra_campo (medicamentos, defensivos, combustível).

Faz match do produto NF-e com dim_catalogo_sap_campo por nome.
Gera SQL ou aplica direto no Supabase.

Uso:
  python importar_nfe_campo.py
  python importar_nfe_campo.py --pasta "C:\\Users\\...\\Desktop\\BAIXAS_SAP\\XML"
  python importar_nfe_campo.py --aplicar
  python importar_nfe_campo.py --dry-run

Coloque os .xml na pasta informada (padrao: Desktop\\BAIXAS_SAP\\XML).
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_SQL = ROOT / "sql" / "007_seed_preco_compra_campo.sql"
SECRETS = ROOT.parent / "requisicao-compras" / ".streamlit" / "secrets.toml"
DEFAULT_PASTA = Path(r"c:\Users\hmauricio\Desktop\BAIXAS_SAP\XML")

MATCH_MIN = 0.55

# Atalho NF-e combustível (catálogo 010_extend)


@dataclass
class ItemNfe:
    nfe: str
    data_compra: str
    fornecedor: str
    cnpj: str
    produto_nfe: str
    codigo_forn: str
    unidade: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    codigo_sap: str | None = None
    match_score: float = 0.0
    match_desc: str = ""


def texto(el, path: str) -> str:
    node = el.find(path)
    return (node.text or "").strip() if node is not None and node.text else ""


def num(s) -> float:
    try:
        return float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def norm_txt(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper().strip())


def score(a: str, b: str) -> float:
    na, nb = norm_txt(a), norm_txt(b)
    if na in nb or nb in na:
        return 0.92
    return SequenceMatcher(None, na, nb).ratio()


def fmt_codigo(raw) -> str:
    s = re.sub(r"\D", "", str(raw).strip())
    return (s.lstrip("0") or "0").zfill(5)


def ler_xml(path: Path) -> list[ItemNfe]:
    return ler_xml_bytes(path.read_bytes())


def ler_xml_bytes(content: bytes) -> list[ItemNfe]:
    tree = ET.parse(BytesIO(content))
    raiz = tree.getroot()
    inf = raiz.find(".//{*}infNFe")
    if inf is None:
        return []

    nfe = texto(inf, ".//{*}ide/{*}nNF")
    demi = texto(inf, ".//{*}ide/{*}dhEmi") or texto(inf, ".//{*}ide/{*}dEmi")
    data = demi[:10] if demi else str(date.today())
    fornecedor = texto(inf, ".//{*}emit/{*}xNome")
    cnpj = texto(inf, ".//{*}emit/{*}CNPJ")

    itens: list[ItemNfe] = []
    for det in inf.findall(".//{*}det"):
        prod = det.find("{*}prod")
        if prod is None:
            continue
        itens.append(ItemNfe(
            nfe=nfe,
            data_compra=data,
            fornecedor=fornecedor,
            cnpj=cnpj,
            produto_nfe=texto(prod, "{*}xProd"),
            codigo_forn=texto(prod, "{*}cProd"),
            unidade=texto(prod, "{*}uCom"),
            quantidade=num(texto(prod, "{*}qCom")),
            valor_unitario=num(texto(prod, "{*}vUnCom")),
            valor_total=num(texto(prod, "{*}vProd")),
        ))
    return itens


def processar_uploads_nfe(
    arquivos: list[tuple[str, bytes]],
    catalogo: list[dict],
    min_score: float = MATCH_MIN,
) -> dict:
    """Processa XMLs enviados pelo Streamlit — match com catálogo SAP."""
    todos: list[ItemNfe] = []
    erros: list[str] = []
    for nome, conteudo in arquivos:
        try:
            itens = ler_xml_bytes(conteudo)
            if not itens:
                erros.append(f"{nome}: XML sem itens de NF-e.")
                continue
            for it in itens:
                todos.append(match_catalogo(it, catalogo, filename=nome))
        except ET.ParseError:
            erros.append(f"{nome}: XML inválido.")
        except Exception as exc:
            erros.append(f"{nome}: {exc}")

    matched = [i for i in todos if i.codigo_sap and i.match_score >= min_score]
    sem_match = [i for i in todos if not i.codigo_sap or i.match_score < min_score]
    return {
        "itens": todos,
        "matched": matched,
        "sem_match": sem_match,
        "erros": erros,
    }


def itens_para_dataframe(itens: list[ItemNfe]) -> "pd.DataFrame":
    import pandas as pd

    rows = []
    for i in itens:
        status = "OK" if i.codigo_sap and i.match_score >= MATCH_MIN else "REVISAR"
        rows.append({
            "NF": i.nfe,
            "Data": i.data_compra,
            "Fornecedor": (i.fornecedor or "")[:40],
            "Produto NF-e": (i.produto_nfe or "")[:50],
            "Cód. SAP": i.codigo_sap or "—",
            "Match catálogo": (i.match_desc or "")[:30],
            "Confiança": f"{i.match_score:.0%}" if i.match_score else "—",
            "Qtd": i.quantidade,
            "Un": i.unidade,
            "R$/un": i.valor_unitario,
            "Status": status,
        })
    return pd.DataFrame(rows)


def load_db_cfg() -> dict:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore
    with open(SECRETS, "rb") as f:
        return tomllib.load(f)["connections"]["supabase"]


def listar_xmls(pasta: Path) -> list[Path]:
    """Lista .xml e .XML (NF-e no Windows)."""
    out = [p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() == ".xml"]
    return sorted(out, key=lambda p: p.name.lower())


def carregar_catalogo_supabase() -> list[dict]:
    import psycopg2

    cfg = load_db_cfg()
    conn = psycopg2.connect(
        host=cfg["host"], port=cfg["port"], database=cfg["database"],
        user=cfg["username"], password=cfg["password"], sslmode="require",
    )
    cur = conn.cursor()
    cur.execute(
        "SELECT codigo_sap, descricao_sap, descricao_resumida FROM dim_catalogo_sap_campo WHERE ativo"
    )
    rows = [{"codigo_sap": r[0], "descricao_sap": r[1], "descricao_resumida": r[2]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def carregar_catalogo_sql_file() -> list[dict]:
    seed = ROOT / "sql" / "003_seed_catalogo_sap_campo.sql"
    if not seed.is_file():
        return []
    catalogo = []
    for m in re.finditer(
        r"\('(\d{5})',\s*'([^']*)',\s*'([^']*)'",
        seed.read_text(encoding="utf-8"),
    ):
        catalogo.append({
            "codigo_sap": m.group(1),
            "descricao_sap": m.group(2).replace("''", "'"),
            "descricao_resumida": m.group(3).replace("''", "'"),
        })
    return catalogo


def match_combustivel_hint(
    produto_nfe: str,
    catalogo: list[dict],
    filename: str = "",
    valor_unitario: float = 0,
) -> tuple[str, str, float] | None:
    """Match diesel S-500 (02335) / S-10 (00162) por NF-e."""
    n = norm_txt(produto_nfe)
    fn = norm_txt(filename)
    cod_alvo = None

    if any(k in fn for k in ("7586", "S-10", "S10", "DIESELS10")):
        cod_alvo = "00162"
    elif any(k in fn for k in ("7569", "S-500", "S500", "ADITIVADO")):
        cod_alvo = "02335"
    elif any(k in n for k in ("S-500", "S500", "ADITIVADO")) and "S-10" not in n and "S10" not in n:
        cod_alvo = "02335"
    elif any(k in n for k in ("S-10", "S10", "DIESEL S10", "DIESEL S-10")):
        cod_alvo = "00162"
    elif "OLEO DIESEL" in n or ("DIESEL" in n and "CLASSE 3" in n):
        # Heurística preço: S-10 costuma ser > R$ 6/L; S-500 aditivado ~ R$ 5,5
        cod_alvo = "00162" if valor_unitario >= 6.0 else "02335"

    if not cod_alvo:
        return None
    for p in catalogo:
        if p.get("codigo_sap") == cod_alvo:
            desc = p.get("descricao_resumida") or p.get("descricao_sap", "")
            return cod_alvo, desc, 0.98
    return None


def match_catalogo(item: ItemNfe, catalogo: list[dict], filename: str = "") -> ItemNfe:
    hint = match_combustivel_hint(
        item.produto_nfe, catalogo, filename=filename, valor_unitario=item.valor_unitario
    )
    if hint:
        item.codigo_sap, item.match_desc, item.match_score = hint[0], hint[1], hint[2]
        return item
    melhor = None
    melhor_score = 0.0
    for p in catalogo:
        for cand in (p.get("descricao_sap"), p.get("descricao_resumida"), p.get("codigo_sap")):
            if not cand:
                continue
            sc = score(item.produto_nfe, cand)
            if sc > melhor_score:
                melhor_score = sc
                melhor = p
    if melhor and melhor_score >= MATCH_MIN:
        item.codigo_sap = melhor["codigo_sap"]
        item.match_score = round(melhor_score, 3)
        item.match_desc = melhor.get("descricao_resumida") or melhor.get("descricao_sap", "")
    return item


def esc(s: str) -> str:
    return str(s or "").replace("'", "''")


def gerar_sql(itens: list[ItemNfe]) -> str:
    hoje = date.today().isoformat()
    matched = [i for i in itens if i.codigo_sap]
    linhas = [
        f"-- Preco compra campo via NF-e — gerado em {hoje}",
        f"-- {len(matched)} itens matched / {len(itens)} total",
        "",
    ]
    if not matched:
        linhas.append("-- Nenhum item matched ao catalogo.")
        return "\n".join(linhas) + "\n"

    linhas.append(
        "INSERT INTO public.preco_compra_campo "
        "(codigo_sap, valor_unitario, nfe, data_compra, fornecedor_nome, quantidade, unidade, observacao)"
    )
    linhas.append("VALUES")
    vals = []
    for i in matched:
        obs = f"NF-e match {i.match_score:.0%}: {i.produto_nfe[:80]}"
        vals.append(
            f"  ('{i.codigo_sap}', {i.valor_unitario}, '{esc(i.nfe)}', '{i.data_compra}', "
            f"'{esc(i.fornecedor)[:120]}', {i.quantidade}, '{esc(i.unidade)}', '{esc(obs)}')"
        )
    linhas.append(",\n".join(vals))
    linhas.append(";")
    linhas.append("")
    linhas.append("-- Atualiza preco referencia no estoque")
    for i in matched:
        linhas.append(
            f"UPDATE public.estoque_sap_campo SET valor_unitario = {i.valor_unitario}, "
            f"atualizado_em = now() WHERE codigo_sap = '{i.codigo_sap}';"
        )
    return "\n".join(linhas) + "\n"


def aplicar_supabase(itens: list[ItemNfe]) -> tuple[int, int]:
    import psycopg2

    cfg = load_db_cfg()
    conn = psycopg2.connect(
        host=cfg["host"], port=cfg["port"], database=cfg["database"],
        user=cfg["username"], password=cfg["password"], sslmode="require",
    )
    conn.autocommit = True
    cur = conn.cursor()
    ok = 0
    for i in itens:
        if not i.codigo_sap:
            continue
        cur.execute(
            """
            INSERT INTO preco_compra_campo
              (codigo_sap, valor_unitario, nfe, data_compra, fornecedor_nome, quantidade, unidade, observacao)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (i.codigo_sap, i.valor_unitario, i.nfe, i.data_compra, i.fornecedor,
             i.quantidade, i.unidade, f"NF-e match {i.match_score:.0%}: {i.produto_nfe[:80]}"),
        )
        cur.execute(
            "UPDATE estoque_sap_campo SET valor_unitario = %s, atualizado_em = now() WHERE codigo_sap = %s",
            (i.valor_unitario, i.codigo_sap),
        )
        ok += 1
    cur.close()
    conn.close()
    return ok, len(itens) - ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", type=Path, default=DEFAULT_PASTA)
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-score", type=float, default=MATCH_MIN)
    args = ap.parse_args()

    pasta = args.pasta
    if not pasta.is_dir():
        pasta.mkdir(parents=True, exist_ok=True)
        print(f"Pasta criada: {pasta}")
        print("Coloque os XML das NF-e la e rode novamente.")
        sys.exit(0)

    xmls = listar_xmls(pasta)
    if not xmls:
        print(f"Nenhum XML em {pasta}")
        print("(Aceita .xml e .XML)")
        sys.exit(1)

    catalogo = carregar_catalogo_supabase() if SECRETS.is_file() else carregar_catalogo_sql_file()
    if not catalogo:
        print("Catalogo nao encontrado (Supabase ou 003_seed).")
        sys.exit(1)

    todos: list[ItemNfe] = []
    for x in xmls:
        itens = ler_xml(x)
        print(f"OK  {x.name}: NF {itens[0].nfe if itens else '?'} — {len(itens)} item(ns)")
        for it in itens:
            todos.append(match_catalogo(it, catalogo, filename=x.name))

    matched = [i for i in todos if i.codigo_sap and i.match_score >= args.min_score]
    sem_match = [i for i in todos if not i.codigo_sap or i.match_score < args.min_score]

    print(f"\nMatched: {len(matched)} | Sem match: {len(sem_match)}")
    for i in matched[:15]:
        print(f"  {i.codigo_sap} {i.match_desc[:30]:30} R${i.valor_unitario:.2f} NF{i.nfe} ({i.match_score:.0%})")
    if sem_match:
        print("\nSem match (revisar manualmente):")
        for i in sem_match[:10]:
            print(f"  - {i.produto_nfe[:60]}")

    sql = gerar_sql(matched)
    OUT_SQL.write_text(sql, encoding="utf-8")
    print(f"\nSQL: {OUT_SQL}")

    if args.dry_run:
        return
    if args.aplicar:
        ok, fail = aplicar_supabase(matched)
        print(f"Supabase: {ok} inseridos, {fail} ignorados.")
    else:
        print("Proximo: cole sql/007 no Supabase OU python importar_nfe_campo.py --aplicar")


if __name__ == "__main__":
    main()
