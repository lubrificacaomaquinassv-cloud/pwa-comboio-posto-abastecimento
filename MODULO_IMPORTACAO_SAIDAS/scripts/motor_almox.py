"""Motor Python — validação, conciliação, registro e refresh API alma-control-center."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import uuid4

import pandas as pd

from baixa_sap_io import importar_movimentos, ler_baixa_bytes
from carregar_estoque_sap import aplicar_supabase_conn, ler_estoque_bytes
from conciliar_baixa_sap import (
    aplicar_lotes,
    carregar_pendentes,
    conciliar,
    marcar_movimentos_conciliados,
)
from db_config import conectar_psycopg2
from lub_sap_io import aplicar_estoque_lub, marcar_consumo_exportado, preparar_estoque_lub

CATEGORIAS_BAIXA = (
    ("medicamentos", "Medicamentos", "Baixas medicamentos (.xlsx)"),
    ("defensivos", "Defensivos", "Baixas defensivos (.xlsx)"),
    ("combustivel", "Combustivel", "Baixas combustível (.xlsx)"),
    ("nutricao", "Nutricao Animal", "Baixas nutrição / TIP (.xlsx)"),
    ("lubrificantes", "Lubrificantes", "Baixas lubrificantes / filtros (.xlsx)"),
)

CATEGORIAS_ESTOQUE = (
    ("medicamentos", "Medicamentos", "Estoque medicamentos (.xlsx)"),
    ("defensivos", "Defensivos", "Estoque defensivos (.xlsx)"),
    ("combustivel", "Combustivel", "Estoque combustível (.xlsx)"),
    ("nutricao", "Nutricao Animal", "Estoque nutrição (.xlsx)"),
    ("lubrificantes", "Lubrificantes", "Estoque lubrificantes (.xlsx)"),
)

SLUG_CATEGORIA = {s: c for s, c, _ in CATEGORIAS_BAIXA}
SLUG_LUB = "lubrificantes"

CAT_WHATSAPP = {"Medicamentos", "Defensivos"}


@dataclass
class ResultadoValidacao:
    baixas: pd.DataFrame = field(default_factory=pd.DataFrame)
    estoque: pd.DataFrame = field(default_factory=pd.DataFrame)
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    arquivos_baixa: list[str] = field(default_factory=list)
    arquivos_estoque: list[str] = field(default_factory=list)


@dataclass
class PreviewConciliacao:
    matches: list[dict] = field(default_factory=list)
    sem_baixa_sap: list[dict] = field(default_factory=list)
    extra_sap: list[dict] = field(default_factory=list)
    total_whatsapp: int = 0
    total_baixas: int = 0


@dataclass
class ResultadoRegistro:
    movimentos_importados: int = 0
    movimentos_erro: int = 0
    estoque_ok: int = 0
    estoque_skip: int = 0
    estoque_lub_ok: int = 0
    consumo_lub_marcados: int = 0
    lotes_conciliados: int = 0
    movimentos_marcados: int = 0
    lote_whatsapp_id: str | None = None
    api_refresh: dict | None = None
    erros: list[str] = field(default_factory=list)


def ler_uploads_baixas(uploads: dict[str, tuple[bytes, str]]) -> ResultadoValidacao:
    """uploads: slug -> (bytes, filename)."""
    res = ResultadoValidacao()
    partes: list[pd.DataFrame] = []
    for slug, (data, name) in uploads.items():
        if not data:
            continue
        try:
            df = ler_baixa_bytes(data, name)
            if slug in SLUG_CATEGORIA:
                df["categoria"] = SLUG_CATEGORIA[slug]
            partes.append(df)
            res.arquivos_baixa.append(name)
        except Exception as e:
            res.erros.append(f"Baixa {name}: {e}")
    if partes:
        res.baixas = pd.concat(partes, ignore_index=True)
        _validar_baixas(res)
    elif not uploads:
        res.erros.append("Nenhum arquivo de baixa SAP enviado.")
    return res


def ler_uploads_estoque(uploads: dict[str, tuple[bytes, str]]) -> ResultadoValidacao:
    res = ResultadoValidacao()
    partes: list[pd.DataFrame] = []
    for slug, (data, name) in uploads.items():
        if not data:
            continue
        try:
            df = ler_estoque_bytes(data, name)
            df["_slug"] = slug
            partes.append(df)
            res.arquivos_estoque.append(name)
        except Exception as e:
            res.erros.append(f"Estoque {name}: {e}")
    if partes:
        res.estoque = pd.concat(partes, ignore_index=True).drop_duplicates(subset=["codigo_sap"], keep="first")
        res.estoque["unidade"] = res.estoque["unidade"].replace({"LI": "LT", "L": "LT"})
    return res


def _validar_baixas(res: ResultadoValidacao) -> None:
    df = res.baixas
    if df.empty:
        res.erros.append("Planilhas de baixa vazias.")
        return
    sem_conta = df[df["conta_contabil"].isna() | (df["conta_contabil"] == "nan")]
    if not sem_conta.empty:
        res.avisos.append(f"{len(sem_conta)} linha(s) sem conta contábil.")
    sem_cat = df[df["categoria"].isna()]
    if not sem_cat.empty:
        res.avisos.append(
            f"{len(sem_cat)} linha(s) sem categoria inferida — renomeie o arquivo "
            "(baixas_medicamentos_*, baixas_defensivos_*, etc.)."
        )
    dup = df.duplicated(subset=["arquivo_hash", "linha_excel"], keep=False)
    if dup.any():
        res.avisos.append(f"{dup.sum()} linha(s) duplicadas no mesmo arquivo.")


def preview_conciliacao(baixas: pd.DataFrame, conn) -> PreviewConciliacao:
    prev = PreviewConciliacao(total_baixas=len(baixas))
    baixas_med_def = baixas[baixas["categoria"].isin(CAT_WHATSAPP)] if not baixas.empty else baixas
    pend = carregar_pendentes(conn)
    prev.total_whatsapp = len(pend)
    if pend.empty or baixas_med_def.empty:
        return prev

    ok_ids, falha, usadas = conciliar(pend, baixas_med_def)
    used_keys = set(usadas)

    for key in used_keys:
        bx_row = baixas_med_def[
            (baixas_med_def["arquivo_hash"] == key[0]) & (baixas_med_def["linha_excel"] == key[1])
        ].iloc[0]
        pend_row = pend[
            (pend["codigo_sap"] == bx_row["codigo_sap"])
            & (pend["quantidade"].astype(float).sub(float(bx_row["quantidade"])).abs() <= 0.05)
        ].head(1)
        if not pend_row.empty:
            pr = pend_row.iloc[0]
            prev.matches.append({
                "responsavel": pr["responsavel_nome"],
                "codigo_sap": pr["codigo_sap"],
                "produto": pr["produto_texto"],
                "qtd_whatsapp": float(pr["quantidade"]),
                "qtd_sap": float(bx_row["quantidade"]),
                "conta": bx_row.get("conta_contabil"),
                "destino": bx_row.get("centro_custo_sap"),
            })

    for f in falha:
        prev.sem_baixa_sap.append({
            "responsavel": f.get("responsavel"),
            "codigo_sap": f.get("codigo_sap"),
            "produto": f.get("produto"),
            "qtd": f.get("qtd_supabase"),
        })

    for _, bx in baixas_med_def.iterrows():
        key = (bx["arquivo_hash"], int(bx["linha_excel"]))
        if key not in used_keys:
            prev.extra_sap.append({
                "codigo_sap": bx["codigo_sap"],
                "qtd": float(bx["quantidade"]),
                "conta": bx.get("conta_contabil"),
                "destino": bx.get("centro_custo_sap"),
                "fonte": bx.get("fonte"),
            })
    return prev


def refresh_api_alma(conn) -> dict:
    cur = conn.cursor()
    try:
        cur.execute("SELECT public.fn_refresh_api_alma()")
        row = cur.fetchone()
        conn.commit()
        if row and row[0]:
            import json

            return json.loads(row[0]) if isinstance(row[0], str) else dict(row[0])
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        if "fn_refresh_api_alma" in str(e) or "does not exist" in str(e).lower():
            return {"erro": "Função fn_refresh_api_alma ausente — rode sql/023_api_painel_alma.sql"}
        raise
    finally:
        cur.close()


def registrar_whatsapp_lote(form: dict, texto: str, conn) -> str:
    """Grava saida_operacional_lote + itens; retorna lote_id."""
    lote_id = str(uuid4())
    now = pd.Timestamp.now(tz="America/Sao_Paulo").isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO saida_operacional_lote (
          id, texto_original, responsavel_nome, destino_texto, id_local, id_talhao,
          status, status_sap, data_referencia, confirmed_at
        ) VALUES (%s::uuid, %s, %s, %s, %s::uuid, %s::uuid, 'confirmado', 'pendente', %s, %s)
        """,
        (
            lote_id,
            texto,
            form.get("responsavel"),
            form.get("destino_texto"),
            form.get("local_id"),
            form.get("talhao_id"),
            str(form.get("data_referencia") or date.today()),
            now,
        ),
    )
    prod_opts = form.get("prod_opts") or {}
    for it in form.get("itens") or []:
        prod = prod_opts.get(it.get("produto_label") or "")
        cur.execute(
            """
            INSERT INTO saida_operacional_item (
              id, lote_id, ordem, texto_linha, produto_texto, quantidade, unidade,
              codigo_sap, id_catalogo, confianca_match
            ) VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, %s::uuid, %s)
            """,
            (
                str(uuid4()),
                lote_id,
                it.get("ordem", 1),
                it.get("texto_linha"),
                it.get("produto_texto"),
                it.get("quantidade"),
                it.get("unidade"),
                prod.get("codigo_sap") if prod else None,
                prod.get("id") if prod else None,
                it.get("confianca"),
            ),
        )
    conn.commit()
    cur.close()
    return lote_id


def executar_registro(
    baixas: pd.DataFrame,
    estoque: pd.DataFrame,
    *,
    conciliar_whatsapp: bool = False,
    whatsapp_form: dict | None = None,
    texto_whatsapp: str = "",
    data_referencia: date | None = None,
) -> ResultadoRegistro:
    out = ResultadoRegistro()
    conn = conectar_psycopg2()
    try:
        if whatsapp_form and texto_whatsapp.strip():
            try:
                out.lote_whatsapp_id = registrar_whatsapp_lote(whatsapp_form, texto_whatsapp, conn)
            except Exception as e:
                out.erros.append(f"WhatsApp: {e}")

        if not baixas.empty:
            n_imp, n_skip = importar_movimentos(conn, baixas, dry_run=False)
            out.movimentos_importados = n_imp
            out.movimentos_erro = n_skip
            if data_referencia and (baixas["categoria"] == "Lubrificantes").any():
                try:
                    out.consumo_lub_marcados = marcar_consumo_exportado(conn, data_referencia)
                except Exception as e:
                    out.erros.append(f"Lub consumo PWA: {e}")

        if conciliar_whatsapp and not baixas.empty:
            baixas_md = baixas[baixas["categoria"].isin(CAT_WHATSAPP)]
            pend = carregar_pendentes(conn)
            if not pend.empty and not baixas_md.empty:
                ok_ids, _, usadas = conciliar(pend, baixas_md)
                out.lotes_conciliados = aplicar_lotes(conn, ok_ids)
                out.movimentos_marcados = marcar_movimentos_conciliados(conn, usadas)

        if not estoque.empty:
            est_lub = estoque[estoque.get("_slug", pd.Series(dtype=str)) == SLUG_LUB].copy()
            est_campo = estoque[estoque.get("_slug", pd.Series(dtype=str)) != SLUG_LUB].copy()
            if not est_lub.empty:
                df_lub = preparar_estoque_lub(est_lub)
                out.estoque_lub_ok = aplicar_estoque_lub(conn, df_lub)
            if not est_campo.empty:
                ok, skip = aplicar_supabase_conn(conn, est_campo.drop(columns=["_slug"], errors="ignore"))
                out.estoque_ok = ok
                out.estoque_skip = skip

        out.api_refresh = refresh_api_alma(conn)
    except Exception as e:
        out.erros.append(str(e))
        conn.rollback()
    finally:
        conn.close()
    return out


def metricas_baixas(baixas: pd.DataFrame) -> dict[str, Any]:
    if baixas.empty:
        return {}
    return {
        "linhas": len(baixas),
        "valor_total": float(baixas["valor_total"].fillna(0).sum()) if "valor_total" in baixas else 0,
        "categorias": baixas["categoria"].value_counts().to_dict() if "categoria" in baixas else {},
        "por_conta": (
            baixas.groupby("conta_contabil")["valor_total"].sum().sort_values(ascending=False).head(10).to_dict()
            if "conta_contabil" in baixas.columns and "valor_total" in baixas.columns
            else {}
        ),
    }


def timeline_df(baixas: pd.DataFrame) -> pd.DataFrame:
    if baixas.empty or "data_baixa" not in baixas.columns:
        return pd.DataFrame()
    g = baixas.groupby(["data_baixa", "categoria"], dropna=False).agg(
        linhas=("codigo_sap", "count"),
        valor=("valor_total", lambda s: float(s.fillna(0).sum())),
    ).reset_index()
    return g.sort_values("data_baixa")


def heatmap_conta_mes(baixas: pd.DataFrame) -> pd.DataFrame:
    if baixas.empty:
        return pd.DataFrame()
    df = baixas.copy()
    df["mes"] = pd.to_datetime(df["data_baixa"]).dt.strftime("%Y-%m")
    df["conta"] = df["conta_contabil"].fillna("Sem conta")
    pivot = df.pivot_table(
        index="conta", columns="mes", values="valor_total", aggfunc="sum", fill_value=0
    )
    return pivot
