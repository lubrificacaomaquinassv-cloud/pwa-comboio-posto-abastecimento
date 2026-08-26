#!/usr/bin/env python3
"""Consulta api_alma_integridade — diagnóstico divergências."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from db_config import conectar_psycopg2

CODIGOS = ("00516", "00457", "02556", "00466", "01954", "02156", "02405", "01800", "00520", "00458")

def main():
    conn = conectar_psycopg2()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT status_integridade, count(*)
        FROM api_alma_integridade
        GROUP BY status_integridade
        ORDER BY 2 DESC
        """
    )
    print("=== RESUMO api_alma_integridade ===")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")

    cur.execute(
        """
        SELECT codigo_sap, nome_produto, categoria, estoque_atual, valor_estoque,
               consumo_30d, baixas_sap_30d, valor_baixas_30d, pendencias, status_integridade
        FROM api_alma_integridade
        WHERE status_integridade ILIKE '%Diverg%'
        ORDER BY abs(coalesce(consumo_30d,0) - coalesce(baixas_sap_30d,0)) DESC
        LIMIT 15
        """
    )
    print("\n=== TOP DIVERGÊNCIAS (consumo WhatsApp vs baixa SAP 30d) ===")
    cols = [d[0] for d in cur.description]
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        diff = float(d["consumo_30d"] or 0) - float(d["baixas_sap_30d"] or 0)
        print(f"  {d['codigo_sap']} {str(d['nome_produto'])[:30]:30} | WA={d['consumo_30d']} SAP={d['baixas_sap_30d']} diff={diff:+.1f} | est={d['estoque_atual']}")

    print("\n=== ITENS DA TELA (screenshot) ===")
    cur.execute(
        """
        SELECT codigo_sap, nome_produto, consumo_30d, baixas_sap_30d, estoque_atual, status_integridade
        FROM api_alma_integridade WHERE codigo_sap = ANY(%s)
        ORDER BY codigo_sap
        """,
        (list(CODIGOS),),
    )
    for r in cur.fetchall():
        print(" ", r)

    # Detalhe WhatsApp vs SAP para 02556 Zapp
    for cod in ("02556", "00516"):
        print(f"\n--- Detalhe {cod} ---")
        cur.execute(
            """
            SELECT l.data_referencia, l.responsavel_nome, i.quantidade, l.status_sap
            FROM saida_operacional_item i
            JOIN saida_operacional_lote l ON l.id = i.lote_id
            WHERE i.codigo_sap = %s AND l.data_referencia >= current_date - 30
            ORDER BY l.data_referencia
            """,
            (cod,),
        )
        wa = cur.fetchall()
        print("  WhatsApp (30d):", wa if wa else "(nenhum)")
        cur.execute(
            """
            SELECT data_baixa, quantidade, conta_contabil, arquivo_fonte
            FROM movimento_baixa_sap
            WHERE codigo_sap = %s AND data_baixa >= current_date - 30
            ORDER BY data_baixa
            """,
            (cod,),
        )
        sap = cur.fetchall()
        print("  SAP baixas (30d):", sap if sap else "(nenhum)")

    conn.close()

if __name__ == "__main__":
    main()
