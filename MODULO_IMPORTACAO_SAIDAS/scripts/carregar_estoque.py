#!/usr/bin/env python3
"""
Atualiza saldos em public.estoque_sap_campo (painel Lovable / dashboard diário).

Uso:
  python scripts/carregar_estoque.py dados/estoque_inclusoes.csv
  python scripts/carregar_estoque.py dados/estoque_inclusoes.csv --dry-run
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from supabase_client import get_client  # noqa: E402


def normalizar_codigo(valor: str) -> str:
    txt = str(valor).strip()
    if txt.endswith(".0") and txt[:-2].isdigit():
        return txt[:-2]
    return txt


def ler_csv(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    out: list[dict] = []
    for row in rows:
        codigo = normalizar_codigo(row.get("codigo_sap", ""))
        if not codigo:
            continue
        qtd = float(str(row.get("em_estoque", "0")).replace(",", "."))
        unidade = (row.get("unidade") or "KG").strip().upper()
        out.append(
            {
                "codigo_sap": codigo,
                "em_estoque": qtd,
                "unidade": unidade,
                "valor_unitario": row.get("valor_unitario") or None,
            }
        )
    return out


def upsert_estoque(itens: list[dict], dry_run: bool = False) -> int:
    if dry_run:
        for item in itens:
            print(f"[dry-run] {item['codigo_sap']} = {item['em_estoque']} {item['unidade']}")
        return len(itens)

    sb = get_client()
    total = 0
    for item in itens:
        sb.table("estoque_sap_campo").upsert(item, on_conflict="codigo_sap").execute()
        total += 1
        print(f"Estoque: {item['codigo_sap']} = {item['em_estoque']} {item['unidade']}")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Atualiza estoque SAP campo")
    parser.add_argument("arquivo", type=Path, help="CSV codigo_sap;em_estoque;unidade")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.arquivo.is_file():
        print(f"Arquivo não encontrado: {args.arquivo}", file=sys.stderr)
        return 1
    itens = ler_csv(args.arquivo)
    print(f"Lendo {len(itens)} saldo(s) de {args.arquivo.name}")
    n = upsert_estoque(itens, dry_run=args.dry_run)
    print(f"Concluído: {n} saldo(s) gravado(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
