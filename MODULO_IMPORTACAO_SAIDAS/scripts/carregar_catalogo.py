#!/usr/bin/env python3
"""
Carrega ou atualiza itens em public.dim_catalogo_sap_campo (catálogo do painel Lovable).

Uso:
  python scripts/carregar_catalogo.py dados/catalogo_inclusoes.csv
  python scripts/carregar_catalogo.py dados/catalogo_inclusoes.csv --dry-run
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from codigo_sap import normalizar_codigo_sap  # noqa: E402
from supabase_client import get_client  # noqa: E402

CAMPOS = (
    "codigo_sap",
    "descricao_sap",
    "descricao_resumida",
    "unidade_estoque",
    "categoria",
    "deposito_sap",
    "ativo",
    "fonte_arquivo",
    "observacao",
)


def ler_csv(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    if not rows:
        raise ValueError(f"Arquivo vazio: {caminho}")
    out: list[dict] = []
    for row in rows:
        item = {k: (row.get(k) or "").strip() for k in CAMPOS if k in row or k in CAMPOS}
        if not item.get("codigo_sap"):
            continue
        item["codigo_sap"] = normalizar_codigo_sap(item["codigo_sap"])
        item.setdefault("ativo", "true")
        item["ativo"] = str(item["ativo"]).lower() in {"1", "true", "sim", "s", "yes", "y"}
        item.setdefault("deposito_sap", "FSV-MAN")
        item.setdefault("categoria", "Defensivos")
        item.setdefault("fonte_arquivo", caminho.name)
        out.append(item)
    return out


def upsert_catalogo(itens: list[dict], dry_run: bool = False) -> tuple[int, int]:
    if dry_run:
        for item in itens:
            print(f"[dry-run] {item['codigo_sap']} — {item.get('descricao_resumida') or item.get('descricao_sap')}")
        return len(itens), 0

    sb = get_client()
    inseridos = 0
    atualizados = 0
    for item in itens:
        codigo = item["codigo_sap"]
        existente = (
            sb.table("dim_catalogo_sap_campo")
            .select("id,codigo_sap")
            .eq("codigo_sap", codigo)
            .limit(1)
            .execute()
        )
        payload = {k: item[k] for k in CAMPOS if k in item and item[k] != ""}
        if existente.data:
            sb.table("dim_catalogo_sap_campo").update(payload).eq("codigo_sap", codigo).execute()
            atualizados += 1
            print(f"Atualizado: {codigo} — {payload.get('descricao_resumida', '')}")
        else:
            sb.table("dim_catalogo_sap_campo").insert(payload).execute()
            inseridos += 1
            print(f"Inserido: {codigo} — {payload.get('descricao_resumida', '')}")
    return inseridos, atualizados


def main() -> int:
    parser = argparse.ArgumentParser(description="Carrega catálogo SAP campo (painel Lovable)")
    parser.add_argument("arquivo", type=Path, help="CSV com colunas do catálogo (; separador)")
    parser.add_argument("--dry-run", action="store_true", help="Somente exibe o que seria enviado")
    args = parser.parse_args()
    if not args.arquivo.is_file():
        print(f"Arquivo não encontrado: {args.arquivo}", file=sys.stderr)
        return 1
    itens = ler_csv(args.arquivo)
    print(f"Lendo {len(itens)} item(ns) de {args.arquivo.name}")
    ins, upd = upsert_catalogo(itens, dry_run=args.dry_run)
    print(f"Concluído: {ins} inserido(s), {upd} atualizado(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
