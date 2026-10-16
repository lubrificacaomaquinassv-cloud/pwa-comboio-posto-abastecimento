"""Persistência SQLite para lançamentos e configuração."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

DB_PATH = Path(__file__).resolve().parent / "data" / "orcamento.db"

CATEGORIAS_FIXAS = [
    "Água",
    "Luz",
    "Internet",
    "Parcela Casa",
    "Plano Funerário",
    "Mercado (fixo)",
    "Combustível",
    "Manutenção Veículo",
    "Dízimo",
    "Primícias",
    "Ofertas Voluntárias",
    "Outros (fixo)",
]

CATEGORIAS_VARIAVEIS = [
    "Supermercado (cartão)",
    "Combustível (cartão)",
    "Lazer",
    "Saúde",
    "Educação",
    "Vestuário",
    "Outros (variável)",
]

_db_initialized = False


def init_db() -> None:
    global _db_initialized
    if _db_initialized:
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS configuracao (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                dia_fechamento INTEGER NOT NULL DEFAULT 22,
                dia_pagamento INTEGER NOT NULL DEFAULT 4,
                renda_padrao REAL NOT NULL DEFAULT 0
            );
            INSERT OR IGNORE INTO configuracao (id) VALUES (1);

            CREATE TABLE IF NOT EXISTS renda_mensal (
                mes TEXT PRIMARY KEY,
                valor REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lancamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_compra TEXT NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('fixa', 'variavel')),
                forma_pagamento TEXT NOT NULL DEFAULT 'pix',
                valor REAL NOT NULL,
                parcela_num INTEGER NOT NULL DEFAULT 1,
                parcelas_total INTEGER NOT NULL DEFAULT 1,
                grupo_parcelamento TEXT,
                fatura_pagamento TEXT,
                mes_competencia TEXT NOT NULL,
                confirmado INTEGER NOT NULL DEFAULT 0,
                proximo_ciclo_forcado INTEGER NOT NULL DEFAULT 0,
                criado_em TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_lanc_fatura ON lancamentos(fatura_pagamento);
            CREATE INDEX IF NOT EXISTS idx_lanc_mes ON lancamentos(mes_competencia);
            CREATE INDEX IF NOT EXISTS idx_lanc_grupo ON lancamentos(grupo_parcelamento);
            """
        )
        _migrate_columns(conn)
        conn.commit()
    finally:
        conn.close()
    _db_initialized = True


def _migrate_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(lancamentos)").fetchall()}
    if "proximo_ciclo_forcado" not in cols:
        conn.execute("ALTER TABLE lancamentos ADD COLUMN proximo_ciclo_forcado INTEGER NOT NULL DEFAULT 0")


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_config() -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM configuracao WHERE id = 1").fetchone()
        return dict(row) if row else {"dia_fechamento": 22, "dia_pagamento": 4, "renda_padrao": 0}


def update_config(dia_fechamento: int, dia_pagamento: int, renda_padrao: float) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE configuracao
            SET dia_fechamento = ?, dia_pagamento = ?, renda_padrao = ?
            WHERE id = 1
            """,
            (dia_fechamento, dia_pagamento, renda_padrao),
        )


def set_renda_mes(mes: str, valor: float) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO renda_mensal (mes, valor) VALUES (?, ?) ON CONFLICT(mes) DO UPDATE SET valor = excluded.valor",
            (mes, valor),
        )


def get_renda_mes(mes: str, renda_padrao: float) -> float:
    with get_conn() as conn:
        row = conn.execute("SELECT valor FROM renda_mensal WHERE mes = ?", (mes,)).fetchone()
        if row:
            return float(row["valor"])
        return renda_padrao


def insert_lancamento(row: Dict[str, Any]) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO lancamentos (
                data_compra, descricao, categoria, tipo, forma_pagamento,
                valor, parcela_num, parcelas_total, grupo_parcelamento,
                fatura_pagamento, mes_competencia, confirmado, proximo_ciclo_forcado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["data_compra"],
                row["descricao"],
                row["categoria"],
                row["tipo"],
                row["forma_pagamento"],
                row["valor"],
                row["parcela_num"],
                row["parcelas_total"],
                row.get("grupo_parcelamento"),
                row.get("fatura_pagamento"),
                row["mes_competencia"],
                1 if row.get("confirmado") else 0,
                1 if row.get("proximo_ciclo_forcado") else 0,
            ),
        )
        return int(cur.lastrowid)


def confirmar_lancamento(lanc_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE lancamentos SET confirmado = 1 WHERE id = ?", (lanc_id,))


def delete_lancamento(lanc_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM lancamentos WHERE id = ?", (lanc_id,))


def delete_grupo_parcelamento(grupo: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM lancamentos WHERE grupo_parcelamento = ?", (grupo,))


def list_lancamentos(
    mes_competencia: Optional[str] = None,
    fatura_pagamento: Optional[str] = None,
    apenas_confirmados: bool = False,
) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM lancamentos WHERE 1=1"
    params: List[Any] = []
    if mes_competencia:
        sql += " AND mes_competencia = ?"
        params.append(mes_competencia)
    if fatura_pagamento:
        sql += " AND fatura_pagamento = ?"
        params.append(fatura_pagamento)
    if apenas_confirmados:
        sql += " AND confirmado = 1"
    sql += " ORDER BY data_compra, id"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def sum_por_fatura(fatura: str, categoria_prefix: Optional[str] = None) -> float:
    sql = "SELECT COALESCE(SUM(valor), 0) FROM lancamentos WHERE confirmado = 1 AND fatura_pagamento = ?"
    params: List[Any] = [fatura]
    if categoria_prefix:
        sql += " AND categoria LIKE ?"
        params.append(categoria_prefix + "%")
    with get_conn() as conn:
        return float(conn.execute(sql, params).fetchone()[0])


def parcelas_encerrando(fatura: str) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM lancamentos
            WHERE confirmado = 1 AND fatura_pagamento = ? AND parcela_num = parcelas_total
            ORDER BY descricao
            """,
            (fatura,),
        ).fetchall()
        return [dict(r) for r in rows]


def total_parcelado_na_fatura(fatura: str) -> float:
    with get_conn() as conn:
        return float(
            conn.execute(
                """
                SELECT COALESCE(SUM(valor), 0) FROM lancamentos
                WHERE confirmado = 1 AND fatura_pagamento = ? AND parcelas_total > 1
                """,
                (fatura,),
            ).fetchone()[0]
        )


def mes_competencia_de(data_compra: date) -> str:
    return f"{data_compra.year:04d}-{data_compra.month:02d}"


def sum_fixas_mes(mes: str) -> float:
    with get_conn() as conn:
        return float(
            conn.execute(
                """
                SELECT COALESCE(SUM(valor), 0) FROM lancamentos
                WHERE confirmado = 1 AND mes_competencia = ? AND tipo = 'fixa'
                """,
                (mes,),
            ).fetchone()[0]
        )


def sum_supermercado_fatura(fatura: str) -> float:
    with get_conn() as conn:
        return float(
            conn.execute(
                """
                SELECT COALESCE(SUM(valor), 0) FROM lancamentos
                WHERE confirmado = 1 AND fatura_pagamento = ?
                  AND (categoria LIKE 'Supermercado%' OR categoria LIKE 'Mercado%')
                """,
                (fatura,),
            ).fetchone()[0]
        )
