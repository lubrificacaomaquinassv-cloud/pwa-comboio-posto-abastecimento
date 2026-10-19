-- Leitura do mapa via API (anon / service_role) — rode DEPOIS do 004 ou sozinho.

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

GRANT SELECT ON vw_dim_talhoes_geojson TO anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION public.api_talhoes_geojson()
RETURNS json
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT coalesce(
        json_agg(row_to_json(t)),
        '[]'::json
    )
    FROM (
        SELECT
            upper(trim(d.codigo)) AS talhao,
            d.classe_uso AS classe,
            l.nome AS retiro,
            d.area_ha AS area_ha_kml,
            ST_AsGeoJSON(d.geom)::json AS geojson
        FROM dim_talhoes d
        LEFT JOIN dim_locais l ON l.id = d.id_local
        WHERE d.geom IS NOT NULL
          AND coalesce(d.ativo, true)
    ) t;
$$;

GRANT EXECUTE ON FUNCTION public.api_talhoes_geojson() TO anon, authenticated, service_role;
