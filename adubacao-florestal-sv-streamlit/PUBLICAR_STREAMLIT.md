# Publicar no Streamlit Cloud

- **Repositório oficial:** `lubrificacaomaquinassv-cloud/adubacao-florestal-sv` (raiz = este código).
- **Espelho no PWA:** pasta `adubacao-florestal-sv-streamlit/` — use **Main file:** `adubacao-florestal-sv-streamlit/app.py`.

## Secrets

```toml
SUPABASE_DB_URL = "postgresql+psycopg://postgres.<ref>:<senha>@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
```

## Banco

1. Executar `sql/003_schema_adubacao_florestal.sql` no Supabase.
2. Carga inicial no PC (planilhas `DADOS_PAINEL`):

```bash
export SUPABASE_DB_URL='...'
python scripts/sync_excel_to_supabase.py \
  --kml /caminho/fazenda_santa_virginia_completo.kml \
  --cobertura /caminho/cobertura.xlsx \
  --base /caminho/base.xlsx
```
