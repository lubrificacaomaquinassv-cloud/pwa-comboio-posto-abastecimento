"""Estoque e controle de baixa — lubrificantes (estoque_lub_sap)."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pandas as pd


def _norm_unidade_lub(u: str) -> str:
    u = str(u or "L").strip().upper()
    if u in ("LT", "LTS", "L", "LI", "LITRO", "LITROS"):
        return "L"
    if u in ("UN", "UND", "UNID"):
        return "UN"
    if u in ("KG",):
        return "KG"
    return u


def preparar_estoque_lub(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["unidade"] = out["unidade"].map(_norm_unidade_lub)
    return out[["codigo_sap", "descricao_sap", "em_estoque", "unidade"]].rename(
        columns={"descricao_sap": "descricao"}
    )


def aplicar_estoque_lub(conn, df: pd.DataFrame) -> int:
    cur = conn.cursor()
    n = 0
    sql = """
        INSERT INTO public.estoque_lub_sap (codigo_sap, descricao, em_estoque, unidade, atualizado_em)
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (codigo_sap) DO UPDATE SET
          descricao = EXCLUDED.descricao,
          em_estoque = EXCLUDED.em_estoque,
          unidade = EXCLUDED.unidade,
          atualizado_em = now()
    """
    for r in df.itertuples(index=False):
        cur.execute(sql, (r.codigo_sap, r.descricao, float(r.em_estoque), r.unidade))
        n += 1
    conn.commit()
    cur.close()
    return n


def marcar_consumo_exportado(conn, data_corte: date, lote: str | None = None) -> int:
    lote = lote or f"BAIXA-LUB-ALMOX-{date.today():%Y%m%d}-{uuid4().hex[:6].upper()}"
    cur = conn.cursor()
    cur.execute(
        """
        SELECT f.id, f.numero_os, f.id_insumo, d.codigo_sap, f.id_frota, f.quantidade, f.created_at
        FROM public.financeiro_lubrificacao f
        LEFT JOIN public.dim_insumo d ON d.id_insumo = f.id_insumo
        LEFT JOIN public.lub_baixa_sap b ON b.financeiro_id = f.id
        WHERE b.id IS NULL
          AND f.quantidade > 0
          AND (f.created_at AT TIME ZONE 'America/Sao_Paulo')::date <= %s
        ORDER BY f.created_at
        """,
        (data_corte,),
    )
    rows = cur.fetchall()
    n = 0
    for fid, numero_os, id_insumo, codigo_sap, id_frota, quantidade, created_at in rows:
        cur.execute(
            """
            INSERT INTO public.lub_baixa_sap (
              financeiro_id, order_number, id_insumo, codigo_sap, id_frota,
              quantidade, data_servico, lote_export
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                fid,
                numero_os or "",
                id_insumo,
                codigo_sap,
                str(id_frota or ""),
                float(quantidade or 0),
                created_at,
                lote,
            ),
        )
        n += cur.rowcount
    conn.commit()
    cur.close()
    return n
