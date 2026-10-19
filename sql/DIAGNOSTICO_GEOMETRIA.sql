-- Cole no DBeaver se o 005 falhar — mostra onde esta a geometria.

SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'dim_talhoes'
ORDER BY ordinal_position;

SELECT f_table_name, f_geometry_column, type
FROM geometry_columns
WHERE f_table_schema = 'public'
ORDER BY f_table_name;
