-- Controle de carga: projeto atual vs. dados legados (projeto anterior no mesmo Supabase)
-- Execute após 003_schema_adubacao_florestal.sql

ALTER TABLE fato_adubacao_cobertura
    ADD COLUMN IF NOT EXISTS projeto_carga TEXT DEFAULT 'legado',
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE fato_adubacao_base
    ADD COLUMN IF NOT EXISTS projeto_carga TEXT DEFAULT 'legado',
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN fato_adubacao_cobertura.projeto_carga IS
    'Identificador da carga (ex: sv_florestal_2026). Linhas antigas permanecem como legado.';
COMMENT ON COLUMN fato_adubacao_cobertura.ativo IS
    'FALSE = lançamento substituído/descontinuado; painel ignora na view oficial.';

CREATE INDEX IF NOT EXISTS idx_fato_cobertura_ativo_projeto
    ON fato_adubacao_cobertura (ativo, projeto_carga);

CREATE INDEX IF NOT EXISTS idx_fato_base_ativo_projeto
    ON fato_adubacao_base (ativo, projeto_carga);

-- Painel / mapa: só lançamentos ativos
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
    projeto_carga,
    CASE
        WHEN area_floresta_ha IS NOT NULL AND area_floresta_ha > 0 AND kg_total IS NOT NULL
        THEN ROUND((kg_total / area_floresta_ha)::numeric, 2)
        ELSE NULL
    END AS dose_realizada_calc_ha
FROM fato_adubacao_cobertura
WHERE ativo = TRUE
ORDER BY talhao, data DESC NULLS LAST, updated_at DESC, id DESC;

-- Resumo para auditoria (rodar no SQL Editor antes/depois da carga)
CREATE OR REPLACE VIEW vw_auditoria_cobertura_por_projeto AS
SELECT
    COALESCE(projeto_carga, 'sem_projeto') AS projeto_carga,
    ativo,
    COUNT(*) AS qtd_lancamentos,
    COUNT(DISTINCT talhao) AS qtd_talhoes,
    MIN(data) AS data_min,
    MAX(data) AS data_max,
    MAX(updated_at) AS ultima_atualizacao
FROM fato_adubacao_cobertura
GROUP BY 1, 2
ORDER BY 1, 2;
