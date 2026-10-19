-- Mapa na API (Streamlit URL + chave) — rode INTEIRO uma vez (Supabase SQL Editor ou DBeaver no MESMO banco do projeto).
-- Nao use o arquivo 004 (geom fixo).

CREATE EXTENSION IF NOT EXISTS postgis;

DO $setup$
DECLARE
    tbl text;
    gcol text;
    cand text;
    sql_view text;
    n bigint;
BEGIN
    FOREACH tbl IN ARRAY ARRAY['dim_talhoes', 'dim_talhao_florestal']
    LOOP
        gcol := NULL;

        SELECT a.attname INTO gcol
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_type t ON a.atttypid = t.oid
        WHERE n.nspname = 'public'
          AND c.relname = tbl
          AND t.typname IN ('geometry', 'geography')
          AND a.attnum > 0
          AND NOT a.attisdropped
        ORDER BY a.attnum
        LIMIT 1;

        IF gcol IS NULL THEN
            SELECT column_name INTO gcol
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = tbl
              AND udt_name IN ('geometry', 'geography')
            LIMIT 1;
        END IF;

        IF gcol IS NULL THEN
            FOREACH cand IN ARRAY ARRAY['geom', 'geometry', 'the_geom', 'shape', 'poligono', 'geometria']
            LOOP
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = tbl
                      AND column_name = cand
                ) THEN
                    gcol := cand;
                    EXIT;
                END IF;
            END LOOP;
        END IF;

        IF gcol IS NULL THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'SELECT COUNT(*) FROM public.%I WHERE %I IS NOT NULL',
            tbl, gcol
        ) INTO n;

        IF n IS NULL OR n = 0 THEN
            CONTINUE;
        END IF;

        IF tbl = 'dim_talhoes' THEN
            sql_view := format($v$
                CREATE OR REPLACE VIEW vw_dim_talhoes_geojson AS
                SELECT
                    upper(trim(d.codigo::text)) AS talhao,
                    d.classe_uso AS classe,
                    l.nome AS retiro,
                    d.area_ha AS area_ha_kml,
                    ST_AsGeoJSON(d.%1$I)::json AS geojson
                FROM public.dim_talhoes d
                LEFT JOIN public.dim_locais l ON l.id = d.id_local
                WHERE d.%1$I IS NOT NULL
                  AND coalesce(d.ativo, true)
            $v$, gcol);
        ELSE
            sql_view := format($v$
                CREATE OR REPLACE VIEW vw_dim_talhoes_geojson AS
                SELECT
                    upper(trim(talhao::text)) AS talhao,
                    classe,
                    retiro,
                    area_ha_kml,
                    ST_AsGeoJSON(%1$I)::json AS geojson
                FROM public.dim_talhao_florestal
                WHERE %1$I IS NOT NULL
            $v$, gcol);
        END IF;

        EXECUTE sql_view;
        RAISE NOTICE 'vw_dim_talhoes_geojson OK — tabela %, coluna %, % linhas com geometria.', tbl, gcol, n;
        RETURN;
    END LOOP;

    RAISE EXCEPTION
        'Nenhuma geometria em dim_talhoes nem dim_talhao_florestal. '
        'Confira PostGIS (CREATE EXTENSION postgis) e rode sql/DIAGNOSTICO_GEOMETRIA.sql.';
END
$setup$;

GRANT SELECT ON vw_dim_talhoes_geojson TO anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION public.api_talhoes_geojson()
RETURNS json
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, extensions
AS $$
    SELECT coalesce(json_agg(row_to_json(t)), '[]'::json)
    FROM (
        SELECT talhao, classe, retiro, area_ha_kml, geojson
        FROM vw_dim_talhoes_geojson
    ) t;
$$;

GRANT EXECUTE ON FUNCTION public.api_talhoes_geojson() TO anon, authenticated, service_role;
