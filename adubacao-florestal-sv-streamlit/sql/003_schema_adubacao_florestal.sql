-- =============================================================================
-- Adubação florestal (cobertura + base) — dimensão talhão + fatos operacionais
-- Execute no SQL Editor do Supabase (PostGIS habilitado no projeto).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- Talhões com geometria (KML / cadastro GIS)
CREATE TABLE IF NOT EXISTS dim_talhao_florestal (
    talhao          TEXT PRIMARY KEY,
    classe          TEXT,
    retiro          TEXT,
    area_ha_kml     NUMERIC(12, 2),
    geom            geometry(MultiPolygon, 4326),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dim_talhao_florestal_geom
    ON dim_talhao_florestal USING GIST (geom);

-- Lançamentos de adubação de cobertura (planilha por retiro/horto)
CREATE TABLE IF NOT EXISTS fato_adubacao_cobertura (
    id                      BIGSERIAL PRIMARY KEY,
    talhao                  TEXT NOT NULL,
    retiro                  TEXT,
    area_total_ha           NUMERIC(12, 2),
    area_floresta_ha        NUMERIC(12, 2),
    fertilizante            TEXT,
    data                    DATE,
    dose_recomendada_ha     NUMERIC(12, 2),
    dose_realizada_ha       NUMERIC(12, 2),
    kg_total                NUMERIC(14, 2),
    operador                TEXT,
    formula_npk             TEXT,
    n_kg                    NUMERIC(14, 2),
    p2o5_kg                 NUMERIC(14, 2),
    k2o_kg                  NUMERIC(14, 2),
    arquivo_origem          TEXT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fato_cobertura_natural UNIQUE (talhao, retiro, data, fertilizante, kg_total)
);

CREATE INDEX IF NOT EXISTS idx_fato_cobertura_talhao
    ON fato_adubacao_cobertura (talhao);

CREATE INDEX IF NOT EXISTS idx_fato_cobertura_retiro
    ON fato_adubacao_cobertura (retiro);

-- Base / subsolagem
CREATE TABLE IF NOT EXISTS fato_adubacao_base (
    id                  BIGSERIAL PRIMARY KEY,
    talhao              TEXT NOT NULL,
    retiro              TEXT,
    area_plantada_ha    NUMERIC(12, 2),
    fertilizante        TEXT,
    dose_ha             NUMERIC(12, 2),
    kg_total            NUMERIC(14, 2),
    prestador           TEXT,
    status              TEXT NOT NULL CHECK (status IN ('Subsolado/Adubado', 'A subsolar')),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fato_base_natural UNIQUE (talhao, retiro, status, fertilizante, kg_total)
);

CREATE INDEX IF NOT EXISTS idx_fato_base_talhao ON fato_adubacao_base (talhao);

-- View: último lançamento de cobertura por talhão (painel / mapa)
CREATE OR REPLACE VIEW vw_cobertura_ultimo_por_talhao AS
SELECT DISTINCT ON (talhao)
    talhao,
    retiro,
    area_total_ha,
    area_floresta_ha,
    fertilizante,
    data,
    dose_recomendada_ha,
    dose_realizada_ha,
    kg_total,
    operador,
    CASE
        WHEN area_floresta_ha IS NOT NULL AND area_floresta_ha > 0 AND kg_total IS NOT NULL
        THEN ROUND((kg_total / area_floresta_ha)::numeric, 2)
        ELSE NULL
    END AS dose_realizada_calc_ha
FROM fato_adubacao_cobertura
ORDER BY talhao, data DESC NULLS LAST, id DESC;

COMMENT ON VIEW vw_cobertura_ultimo_por_talhao IS
    'Último registro de cobertura por talhão; dose_realizada_calc_ha = Total Gasto / Floresta (há).';
