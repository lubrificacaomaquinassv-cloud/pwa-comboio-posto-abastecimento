-- Views Lovable + PostgREST — Adubação florestal (mesma fonte do Streamlit)
-- Tabelas: fato_adubacao_cobertura, fato_adubacao_base
-- Execute após 003 e (recomendado) 004.

-- 1) Lançamentos de cobertura (flat, calculadora NPK)
CREATE OR REPLACE VIEW vw_api_adubacao_cobertura AS
SELECT
    c.id,
    c.talhao,
    c.retiro,
    c.area_total_ha,
    c.area_floresta_ha,
    c.fertilizante,
    c.data,
    c.dose_recomendada_ha,
    c.dose_realizada_ha,
    c.kg_total,
    c.operador,
    c.formula_npk,
    c.n_kg,
    c.p2o5_kg,
    c.k2o_kg,
    CASE
        WHEN c.area_floresta_ha > 0 AND c.kg_total IS NOT NULL
        THEN ROUND((c.kg_total / c.area_floresta_ha)::numeric, 2)
        ELSE NULL
    END AS realizado_kg_ha,
    c.arquivo_origem,
    c.projeto_carga,
    c.updated_at
FROM fato_adubacao_cobertura c
WHERE c.ativo IS DISTINCT FROM FALSE;

-- 2) Último lançamento por talhão (mapa / ficha)
CREATE OR REPLACE VIEW vw_adubacao_ultimo_por_talhao AS
SELECT DISTINCT ON (talhao)
    id,
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
    formula_npk,
    n_kg,
    p2o5_kg,
    k2o_kg,
    realizado_kg_ha
FROM vw_api_adubacao_cobertura
ORDER BY talhao, data DESC NULLS LAST, id DESC;

-- 3) Resumo por retiro (KPIs Lovable)
CREATE OR REPLACE VIEW vw_adubacao_resumo_retiro AS
SELECT
    COALESCE(retiro, 'SEM_RETIRO') AS retiro,
    COUNT(*)::int AS qtd_lancamentos,
    COUNT(DISTINCT talhao)::int AS qtd_talhoes,
    ROUND(SUM(area_total_ha)::numeric, 2) AS area_total_ha,
    ROUND(SUM(kg_total)::numeric, 2) AS kg_total,
    ROUND(SUM(n_kg)::numeric, 2) AS n_kg_total,
    ROUND(SUM(p2o5_kg)::numeric, 2) AS p2o5_kg_total,
    ROUND(SUM(k2o_kg)::numeric, 2) AS k2o_kg_total
FROM vw_api_adubacao_cobertura
GROUP BY 1;

-- 4) Agregado por talhão
CREATE OR REPLACE VIEW vw_adubacao_por_talhao AS
SELECT
    talhao,
    MAX(retiro) AS retiro_principal,
    COUNT(*)::int AS qtd_lancamentos,
    ROUND(SUM(area_total_ha)::numeric, 2) AS area_adubada_ha,
    ROUND(SUM(kg_total)::numeric, 2) AS kg_total,
    ROUND(SUM(n_kg)::numeric, 2) AS n_kg_total,
    MAX(data) AS ultima_data,
    STRING_AGG(DISTINCT fertilizante, ', ' ORDER BY fertilizante) AS fertilizantes
FROM vw_api_adubacao_cobertura
GROUP BY talhao;

-- 5) Join mapa (dim_talhoes / dim_talhao_florestal cadastro)
CREATE OR REPLACE VIEW vw_adubacao_mapa AS
SELECT
    t.talhao,
    t.retiro_principal,
    t.area_adubada_ha,
    t.kg_total,
    t.n_kg_total,
    t.ultima_data,
    t.fertilizantes,
    d.classe,
    d.area_ha_kml AS area_cadastro_ha
FROM vw_adubacao_por_talhao t
LEFT JOIN dim_talhao_florestal d ON d.talhao = t.talhao;

-- 6) Base / subsolagem (flat)
CREATE OR REPLACE VIEW vw_api_adubacao_base AS
SELECT
    b.id,
    b.talhao,
    b.retiro,
    b.area_plantada_ha,
    b.fertilizante,
    b.dose_ha,
    b.kg_total,
    b.prestador,
    b.status,
    b.projeto_carga,
    b.updated_at
FROM fato_adubacao_base b
WHERE b.ativo IS DISTINCT FROM FALSE;

COMMENT ON VIEW vw_api_adubacao_cobertura IS
    'Lovable/PostgREST: lançamentos de cobertura (NPK + doses). Mesma base do painel Streamlit.';
