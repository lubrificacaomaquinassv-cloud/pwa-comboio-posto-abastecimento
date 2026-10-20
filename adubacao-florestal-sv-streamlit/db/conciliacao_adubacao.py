"""Concilia planilhas DADOS_PAINEL com Supabase (projeto anterior vs. carga atual)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import pandas as pd
from sqlalchemy.engine import Engine

from db.supabase_io import carregar_base, carregar_cobertura
from ingestion.talhao_codigo import normalizar_coluna_talhao

CHAVE_COBERTURA = ["talhao", "retiro", "data", "fertilizante", "kg_total"]
CHAVE_BASE = ["talhao", "retiro", "status", "fertilizante", "kg_total"]

CAMPOS_COMPARAR_COBERTURA = [
    "area_total_ha",
    "area_floresta_ha",
    "dose_recomendada_ha",
    "dose_realizada_ha",
    "operador",
]


def _norm_val(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, (datetime, date)):
        return v.isoformat()[:10]
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d") if pd.notna(v) else ""
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v).strip().upper()


def _chave_row(row: pd.Series, cols: list[str]) -> tuple[str, ...]:
    return tuple(_norm_val(row.get(c)) for c in cols)


def _assinatura_mudanca(row: pd.Series, campos: list[str]) -> str:
    blob = "|".join(_norm_val(row.get(c)) for c in campos)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _prep_cobertura(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = normalizar_coluna_talhao(df.copy())
    if "data" in out.columns:
        out["data"] = pd.to_datetime(out["data"], errors="coerce").dt.date
    for c in CHAVE_COBERTURA + CAMPOS_COMPARAR_COBERTURA:
        if c not in out.columns:
            out[c] = None
    out = out[out["talhao"].notna()].copy()
    out["_chave"] = out.apply(lambda r: _chave_row(r, CHAVE_COBERTURA), axis=1)
    out["_sig"] = out.apply(lambda r: _assinatura_mudanca(r, CAMPOS_COMPARAR_COBERTURA), axis=1)
    return out


def _prep_base(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = normalizar_coluna_talhao(df.copy())
    for c in CHAVE_BASE + ["area_plantada_ha", "dose_ha", "prestador"]:
        if c not in out.columns:
            out[c] = None
    out = out[out["talhao"].notna()].copy()
    out["_chave"] = out.apply(lambda r: _chave_row(r, CHAVE_BASE), axis=1)
    return out


@dataclass
class RelatorioConciliacao:
    projeto_atual: str
    cobertura_planilha: int = 0
    cobertura_supabase_ativo: int = 0
    cobertura_supabase_legado_inativo: int = 0
    cobertura_novos: int = 0
    cobertura_iguais: int = 0
    cobertura_alterados: int = 0
    cobertura_so_supabase: int = 0
    talhoes_planilha: int = 0
    talhoes_supabase_ativos: int = 0
    talhoes_so_legado_supabase: list[str] = field(default_factory=list)
    amostra_alterados: list[dict] = field(default_factory=list)
    amostra_so_supabase: list[dict] = field(default_factory=list)
    por_arquivo_origem_supabase: dict[str, int] = field(default_factory=dict)
    por_projeto_supabase: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "projeto_atual": self.projeto_atual,
            "cobertura": {
                "planilha_linhas": self.cobertura_planilha,
                "supabase_ativo": self.cobertura_supabase_ativo,
                "supabase_legado_inativo": self.cobertura_supabase_legado_inativo,
                "novos_na_planilha": self.cobertura_novos,
                "iguais": self.cobertura_iguais,
                "alterados": self.cobertura_alterados,
                "so_no_supabase": self.cobertura_so_supabase,
            },
            "talhoes": {
                "na_planilha": self.talhoes_planilha,
                "ativos_supabase": self.talhoes_supabase_ativos,
                "so_legado_supabase_amostra": self.talhoes_so_legado_supabase[:30],
            },
            "supabase_por_arquivo_origem": self.por_arquivo_origem_supabase,
            "supabase_por_projeto_carga": self.por_projeto_supabase,
            "amostra_alterados": self.amostra_alterados[:15],
            "amostra_so_supabase": self.amostra_so_supabase[:15],
        }


def conciliar_cobertura(
    df_excel: pd.DataFrame,
    df_db: pd.DataFrame,
    *,
    projeto_atual: str,
) -> tuple[RelatorioConciliacao, pd.DataFrame]:
    """
    Compara planilha × Supabase.
    Retorna relatório e DataFrame só com linhas a gravar (novas + alteradas).
    """
    rel = RelatorioConciliacao(projeto_atual=projeto_atual)
    ex = _prep_cobertura(df_excel)
    db = _prep_cobertura(df_db)

    rel.cobertura_planilha = len(ex)
    rel.talhoes_planilha = int(ex["talhao"].nunique()) if len(ex) else 0

    if "ativo" in db.columns:
        db_ativo = db[db["ativo"] != False].copy()  # noqa: E712
        db_inativo = db[db["ativo"] == False].copy()  # noqa: E712
    else:
        db_ativo = db.copy()
        db_inativo = pd.DataFrame()

    rel.cobertura_supabase_ativo = len(db_ativo)
    rel.cobertura_supabase_legado_inativo = len(db_inativo)

    if "arquivo_origem" in db.columns:
        rel.por_arquivo_origem_supabase = (
            db["arquivo_origem"].fillna("(null)").astype(str).value_counts().head(20).to_dict()
        )
    if "projeto_carga" in db.columns:
        rel.por_projeto_supabase = (
            db["projeto_carga"].fillna("legado").astype(str).value_counts().to_dict()
        )

    rel.talhoes_supabase_ativos = int(db_ativo["talhao"].nunique()) if len(db_ativo) else 0
    tal_plan = set(ex["talhao"].unique()) if len(ex) else set()
    tal_db = set(db_ativo["talhao"].unique()) if len(db_ativo) else set()
    rel.talhoes_so_legado_supabase = sorted(tal_db - tal_plan)[:50]

    map_db = {row["_chave"]: row for _, row in db_ativo.iterrows()}
    keys_ex = set(ex["_chave"])
    keys_db = set(map_db.keys())

    rel.cobertura_so_supabase = len(keys_db - keys_ex)
    for k in list(keys_db - keys_ex)[:15]:
        r = map_db[k]
        rel.amostra_so_supabase.append(
            {
                "talhao": r.get("talhao"),
                "retiro": r.get("retiro"),
                "data": str(r.get("data")),
                "fertilizante": r.get("fertilizante"),
                "kg_total": r.get("kg_total"),
                "projeto_carga": r.get("projeto_carga"),
                "arquivo_origem": r.get("arquivo_origem"),
            }
        )

    gravar_partes = []
    for _, row in ex.iterrows():
        k = row["_chave"]
        if k not in map_db:
            rel.cobertura_novos += 1
            gravar_partes.append(row)
            continue
        db_row = map_db[k]
        if row["_sig"] == db_row["_sig"]:
            rel.cobertura_iguais += 1
        else:
            rel.cobertura_alterados += 1
            if len(rel.amostra_alterados) < 15:
                rel.amostra_alterados.append(
                    {
                        "talhao": row.get("talhao"),
                        "retiro": row.get("retiro"),
                        "data": str(row.get("data")),
                        "campo_exemplo": "area_floresta_ha",
                        "planilha": row.get("area_floresta_ha"),
                        "supabase": db_row.get("area_floresta_ha"),
                    }
                )
            gravar_partes.append(row)

    df_gravar = pd.DataFrame(gravar_partes) if gravar_partes else pd.DataFrame()
    if not df_gravar.empty:
        df_gravar = df_gravar.drop(columns=["_chave", "_sig"], errors="ignore")
    return rel, df_gravar


def desativar_cobertura_fora_da_planilha_por_talhao(
    engine: Engine,
    df_excel: pd.DataFrame,
    *,
    projeto_atual: str,
) -> int:
    """
    Para talhões presentes na planilha: desativa lançamentos ativos no Supabase
    cuja chave natural não está na planilha (substitui histórico daquele talhão).
    Talhões que existem só no projeto anterior e não aparecem na planilha permanecem ativos.
    """
    from sqlalchemy import text

    from db.supabase_io import _coluna_existe

    if not _coluna_existe(engine, "fato_adubacao_cobertura", "ativo"):
        print(
            "Aviso: coluna 'ativo' ausente — rode sql/004_controle_projeto_legado.sql "
            "(sync continua só com upsert, sem desativar legado)."
        )
        return 0

    ex = _prep_cobertura(df_excel)
    if ex.empty:
        return 0
    chaves_ex = set(ex["_chave"])
    talhoes = sorted(ex["talhao"].unique())

    sql_sel = text(
        """
        SELECT id, talhao, retiro, data, fertilizante, kg_total
        FROM fato_adubacao_cobertura
        WHERE ativo = TRUE AND talhao = ANY(:talhoes)
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql_sel, {"talhoes": talhoes}).mappings().all()

    ids_desativar = []
    for r in rows:
        data_val = r["data"]
        if hasattr(data_val, "isoformat"):
            data_val = data_val.isoformat()[:10]
        chave = (
            _norm_val(r["talhao"]),
            _norm_val(r["retiro"]),
            _norm_val(data_val),
            _norm_val(r["fertilizante"]),
            _norm_val(r["kg_total"]),
        )
        if chave not in chaves_ex:
            ids_desativar.append(r["id"])

    if not ids_desativar:
        return 0

    sql_upd = text(
        """
        UPDATE fato_adubacao_cobertura
        SET ativo = FALSE,
            updated_at = now(),
            projeto_carga = COALESCE(projeto_carga, 'legado')
        WHERE id = ANY(:ids)
        """
    )
    with engine.begin() as conn:
        conn.execute(sql_upd, {"ids": ids_desativar})
    return len(ids_desativar)


def carregar_cobertura_todos(engine: Engine) -> pd.DataFrame:
    """Inclui inativos para auditoria."""
    from sqlalchemy import text

    from db.supabase_io import tabela_existe

    if not tabela_existe(engine, "fato_adubacao_cobertura"):
        return pd.DataFrame()
    df = pd.read_sql(text("SELECT * FROM fato_adubacao_cobertura ORDER BY talhao, data"), engine)
    ren = {"n_kg": "N_kg", "p2o5_kg": "P2O5_kg", "k2o_kg": "K2O_kg"}
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    return normalizar_coluna_talhao(df)


def relatorio_json(rel: RelatorioConciliacao) -> str:
    return json.dumps(rel.to_dict(), ensure_ascii=False, indent=2)
