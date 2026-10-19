-- Rode no DBeaver ANTES do 005. Se total = 0, falta carregar o KML no PC.

SELECT count(*) AS poligonos_dim_talhao_florestal
FROM public.dim_talhao_florestal
WHERE geom IS NOT NULL;
