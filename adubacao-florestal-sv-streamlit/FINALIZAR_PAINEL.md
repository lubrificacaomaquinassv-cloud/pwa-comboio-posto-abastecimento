# Finalizar painel — dados de adubação no mapa

## Checklist (ordem)

### 1. Schema no Supabase (uma vez)
SQL Editor → executar `sql/003_schema_adubacao_florestal.sql`.

### 2. Carga das planilhas (Desktop\DADOS_PAINEL → banco)

```powershell
cd adubacao-florestal-sv-streamlit
$env:SUPABASE_DB_URL = "postgresql+psycopg://postgres.SEU_REF:SUA_SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
powershell -ExecutionPolicy Bypass -File scripts\CARGA_DADOS_PAINEL.ps1
```

Confirme no Supabase → Table Editor → `fato_adubacao_cobertura` com linhas.

### 3. Streamlit Cloud — Secrets

**Mínimo para ler adubação (sem postgres no painel):**
```toml
SUPABASE_URL = "https://SEU_REF.supabase.co"
SUPABASE_KEY = "service_role_..." 
```

**Completo (mapa GIS no banco + carga pelo painel):**
```toml
SUPABASE_DB_URL = "postgresql+psycopg://..."
SUPABASE_URL = "https://..."
SUPABASE_KEY = "..."
```

| Campo | Main file |
|--------|-----------|
| Branch | `cursor/fix-ficha-talhao-clique-fbe9` (ou `main` após merge) |
| App | `adubacao-florestal-sv-streamlit/app.py` |

**Reboot app.** Build esperado: **`2026.10.20-dados-adubacao-final`**.

### 4. No painel
- Origem: **☁️ Supabase (oficial)**
- Acima do mapa: linha “**N talhões cruzados com o mapa**” (> 0)
- Clique no talhão → ficha com fertilizante (se houver lançamento)

### 5. Alternativa sem commitar planilhas no Git
Copie xlsx + kml para `adubacao-florestal-sv-streamlit/dados/` no servidor (deploy), aba **☁️ Supabase** → **Executar sync dados/ → Supabase**.

Ou GitHub Actions: secret `SUPABASE_DB_URL` + push em `dados/`.
