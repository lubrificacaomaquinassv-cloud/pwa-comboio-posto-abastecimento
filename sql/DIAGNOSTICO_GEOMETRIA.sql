-- Cole no DBeaver / Supabase SQL Editor se o 005 falhar.

SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('postgis', 'postgis_raster');

SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('dim_talhoes', 'dim_talhao_florestal')
ORDER BY table_name, ordinal_position;

SELECT c.relname AS tabela, a.attname AS coluna_geom, t.typname AS tipo
FROM pg_attribute a
JOIN pg_class c ON a.attrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
JOIN pg_type t ON a.atttypid = t.oid
WHERE n.nspname = 'public'
  AND c.relname IN ('dim_talhoes', 'dim_talhao_florestal')
  AND t.typname IN ('geometry', 'geography')
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY c.relname, a.attnum;
