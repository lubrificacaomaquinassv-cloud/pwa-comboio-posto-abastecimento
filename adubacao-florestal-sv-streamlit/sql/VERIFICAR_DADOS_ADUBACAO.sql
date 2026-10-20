-- Use ESTAS consultas no DBeaver / SQL Editor (funcionam só com sql/003).
-- Se você já rodou sql/004, pode usar também as views do sql/005.

-- 1) Quantos lançamentos de cobertura existem?
SELECT COUNT(*) AS total_cobertura FROM fato_adubacao_cobertura;

-- 2) Amostra (sem coluna "ativo" — não precisa do 004)
SELECT talhao, retiro, fertilizante, data, kg_total, area_floresta_ha, arquivo_origem
FROM fato_adubacao_cobertura
ORDER BY talhao, data
LIMIT 10;

-- 3) Por retiro
SELECT retiro, COUNT(*) AS lancamentos, COUNT(DISTINCT talhao) AS talhoes
FROM fato_adubacao_cobertura
GROUP BY retiro
ORDER BY retiro;

-- Depois de rodar sql/004 + sql/005:
-- SELECT COUNT(*) FROM fato_adubacao_cobertura WHERE ativo IS DISTINCT FROM FALSE;
-- SELECT * FROM vw_api_adubacao_cobertura LIMIT 5;
