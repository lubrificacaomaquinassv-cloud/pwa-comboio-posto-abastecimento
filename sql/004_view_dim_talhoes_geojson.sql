-- View para o painel ler o mapa via API Supabase (URL + chave), sem senha Postgres.
-- Rode uma vez no SQL Editor.

CREATE OR REPLACE VIEW vw_dim_talhoes_geojson AS
SELECT
    upper(trim(d.codigo)) AS talhao,
    d.classe_uso AS classe,
    l.nome AS retiro,
    d.area_ha AS area_ha_kml,
    ST_AsGeoJSON(d.geom)::json AS geojson
FROM public.dim_talhoes d
LEFT JOIN public.dim_locais l ON l.id = d.id_local
WHERE d.geom IS NOT NULL
  AND coalesce(d.ativo, true);

COMMENT ON VIEW vw_dim_talhoes_geojson IS
    'Talhões com geometria GeoJSON para Streamlit (PostgREST / SUPABASE_KEY).';

-- Permite leitura via API (ajuste RLS do seu projeto se necessário)
GRANT SELECT ON vw_dim_talhoes_geojson TO anon, authenticated, service_role;
