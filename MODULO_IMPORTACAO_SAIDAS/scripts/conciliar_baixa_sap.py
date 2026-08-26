#!/usr/bin/env python3
"""Concilia WhatsApp x Excel baixa SAP + importa movimento contábil.

Uso:
  python conciliar_baixa_sap.py
  python conciliar_baixa_sap.py --excel historico\\baixas_estoque_defensivos_21_08_2026.xlsx
  python conciliar_baixa_sap.py --aplicar
  python conciliar_baixa_sap.py --aplicar --sem-importar   (só concilia, não reimporta)

Pasta padrão: Desktop\\BAIXAS_SAP e subpasta historico\\
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from db_config import load_db_cfg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from baixa_sap_io import importar_movimentos, ler_baixa_excel, listar_excel_baixas

DEFAULT_PASTA = Path(r"c:\Users\hmauricio\Desktop\BAIXAS_SAP")


def qtd_bate(a: float, b: float, tol: float = 0.05) -> bool:
    return abs(float(a) - float(b)) <= tol


def carregar_pendentes(conn) -> pd.DataFrame:
    sql = """
        SELECT l.id AS lote_id, l.data_referencia, l.responsavel_nome, l.status_sap,
               i.id AS item_id, i.codigo_sap, i.quantidade, i.unidade, i.produto_texto
        FROM saida_operacional_lote l
        JOIN saida_operacional_item i ON i.lote_id = l.id
        WHERE l.status_sap IN ('pendente', 'baixado')
        ORDER BY l.data_referencia, l.created_at
    """
    return pd.read_sql(sql, conn)


def conciliar(pendentes: pd.DataFrame, baixas: pd.DataFrame) -> tuple[list[str], list[dict], list[tuple]]:
    conciliados: list[str] = []
    nao: list[dict] = []
    baixas_usadas: list[tuple] = []
    used_idx: set[int] = set()

    for _, row in pendentes.iterrows():
        cod = row["codigo_sap"]
        qtd = float(row["quantidade"])
        match_idx = None
        for idx, bx in baixas.iterrows():
            if idx in used_idx:
                continue
            if bx["codigo_sap"] == cod and qtd_bate(bx["quantidade"], qtd):
                match_idx = idx
                break
        if match_idx is not None:
            used_idx.add(match_idx)
            bx = baixas.loc[match_idx]
            baixas_usadas.append((bx["arquivo_hash"], int(bx["linha_excel"])))
            conciliados.append(str(row["lote_id"]))
        else:
            nao.append({
                "lote_id": str(row["lote_id"]),
                "responsavel": row["responsavel_nome"],
                "codigo_sap": cod,
                "qtd_supabase": qtd,
                "produto": row["produto_texto"],
            })
    return list(set(conciliados)), nao, baixas_usadas


def aplicar_lotes(conn, lote_ids: list[str]) -> int:
    if not lote_ids:
        return 0
    cur = conn.cursor()
    n = 0
    for lid in lote_ids:
        cur.execute(
            """
            UPDATE saida_operacional_lote
            SET status_sap = 'conciliado', data_baixa_sap = coalesce(data_baixa_sap, now())
            WHERE id = %s::uuid
            """,
            (lid,),
        )
        n += cur.rowcount
    conn.commit()
    cur.close()
    return n


def marcar_movimentos_conciliados(conn, baixas_usadas: list[tuple]) -> int:
    if not baixas_usadas:
        return 0
    cur = conn.cursor()
    n = 0
    for arquivo_hash, linha_excel in baixas_usadas:
        cur.execute(
            """
            UPDATE movimento_baixa_sap
            SET conciliado_whatsapp = true
            WHERE arquivo_hash = %s AND linha_excel = %s
            """,
            (arquivo_hash, linha_excel),
        )
        n += cur.rowcount
    conn.commit()
    cur.close()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", type=Path, action="append", help="Arquivo baixa SAP")
    ap.add_argument("--pasta", type=Path, default=DEFAULT_PASTA)
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--sem-importar", action="store_true", help="Não grava movimento_baixa_sap")
    ap.add_argument(
        "--somente-importar",
        action="store_true",
        help="Só grava movimento contábil (Combustível/TIP — sem conciliar WhatsApp)",
    )
    ap.add_argument(
        "--categoria",
        choices=("med-def", "combustivel", "nutricao", "todas"),
        default="med-def",
        help="med-def=medicamentos+defensivos (padrão); combustivel; nutricao; todas",
    )
    ap.add_argument("--dry-run", action="store_true", default=True)
    args = ap.parse_args()
    if args.aplicar:
        args.dry_run = False

    cat_map = {
        "med-def": {"Medicamentos", "Defensivos"},
        "combustivel": {"Combustivel"},
        "nutricao": {"Nutricao Animal"},
        "todas": None,
    }
    cats = cat_map[args.categoria]

    paths = args.excel or listar_excel_baixas(args.pasta, categorias=cats)
    if not paths:
        print(f"Nenhum Excel de baixa ({args.categoria}) em {args.pasta} ou historico\\")
        return

    baixas = pd.concat([ler_baixa_excel(p) for p in paths], ignore_index=True)
    print(f"Excel SAP: {len(baixas)} linhas de {len(paths)} arquivo(s)")
    cols_show = ["codigo_sap", "quantidade", "conta_contabil", "centro_custo_sap", "fonte"]
    cols_show = [c for c in cols_show if c in baixas.columns]
    print(baixas[cols_show].head(15).to_string(index=False))
    if len(baixas) > 15:
        print(f"  ... +{len(baixas) - 15} linhas")

    try:
        cfg = load_db_cfg()
    except FileNotFoundError as e:
        print(str(e))
        return
    import psycopg2

    conn = psycopg2.connect(
        host=cfg["host"], port=cfg["port"], database=cfg["database"],
        user=cfg["username"], password=cfg["password"], sslmode="require",
    )

    if not args.sem_importar:
        try:
            n_imp, n_skip = importar_movimentos(conn, baixas, dry_run=args.dry_run)
            modo = "Dry-run" if args.dry_run else "Gravado"
            print(f"\nMovimento contábil ({modo}): {n_imp} linha(s)" + (f", {n_skip} erro(s)" if n_skip else ""))
        except Exception as e:
            if "movimento_baixa_sap" in str(e) and "does not exist" in str(e).lower():
                print("\nTabela movimento_baixa_sap ausente. Rode sql/021_movimento_baixa_sap.sql no Supabase.")
                conn.close()
                return
            raise

    if args.somente_importar or args.categoria in ("combustivel", "nutricao"):
        if args.aplicar:
            try:
                from motor_almox import refresh_api_alma
                r = refresh_api_alma(conn)
                print(f"\nAPI alma-control-center atualizada: {r}")
            except Exception as e:
                print(f"\nAVISO: refresh api_alma falhou: {e}")
        print("\nModo somente-importar: movimento contábil gravado, sem conciliação WhatsApp.")
        conn.close()
        return

    pend = carregar_pendentes(conn)
    print(f"\nSupabase pendentes/baixados: {len(pend)} item(ns)")
    if pend.empty:
        print("Nada a conciliar com WhatsApp.")
        conn.close()
        return

    ok_ids, falha, usadas = conciliar(pend, baixas)
    lotes_ok = list(set(ok_ids))
    print(f"\nMatch WhatsApp: {len(ok_ids)} item | {len(lotes_ok)} lote(s) | Sem match: {len(falha)}")
    for lid in lotes_ok:
        print(f"  OK lote {lid[:8]}...")
    for f in falha[:10]:
        print(
            f"  ? {f['responsavel']} {f['codigo_sap']} qtd={f['qtd_supabase']} "
            f"({f['produto']})"
        )

    if args.dry_run:
        print("\nDry-run. Use --aplicar para gravar conciliado + movimento contábil.")
    else:
        n = aplicar_lotes(conn, ok_ids)
        m = marcar_movimentos_conciliados(conn, usadas)
        print(f"\nLotes conciliados: {n} | Movimentos marcados: {m}")
        try:
            from motor_almox import refresh_api_alma
            r = refresh_api_alma(conn)
            print(f"API alma-control-center: {r}")
        except Exception as e:
            print(f"AVISO: refresh api_alma falhou: {e}")

    conn.close()


if __name__ == "__main__":
    main()
