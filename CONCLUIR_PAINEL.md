# Concluir painel (Streamlit + mapa Supabase)

## O que o Cloud Agent já faz sozinho

- Código no GitHub (`painel-adubacao` / `adubacao-florestal-sv`)
- Workflow **Supabase mapa completo** (KML + SQL) se você configurar 1 secret

## O que você precisa fazer (1× cada)

### 1) GitHub — secret para Actions

Repositório: `lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento`

**Settings → Secrets and variables → Actions → New repository secret**

| Nome | Valor |
|------|--------|
| `SUPABASE_DB_URL` | `postgresql+psycopg://postgres.SEU_REF:SENHA_DATABASE@aws-1-sa-east-1.pooler.supabase.com:6543/postgres` |

(Senha = **Database password**, não anon key.)

### 2) KML no GitHub (para o workflow)

Copie o arquivo `.kml` para:

`dados/fazenda_santa_virginia_completo.kml`

Commit + push (pode ser privado — repo já é seu).

### 3) Rodar workflow

**Actions → Supabase mapa completo → Run workflow**

Deixe o caminho padrão do KML. Aguarde verde.

### 4) Streamlit Cloud

**Manage app → Settings**

| Campo | Valor |
|--------|--------|
| Repository | `lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento` |
| Branch | `painel-adubacao` |
| Main file | `app.py` |

**Secrets** (só API, sem senha Postgres):

```toml
SUPABASE_URL = "https://azhpxhrwhegfysoeqmft.supabase.co"
SUPABASE_KEY = "sua anon ou service_role"
```

**Reboot app** → sidebar: GIS com polígonos + build `2026.10.20-api-rpc`.

## Lovable

Já consome `vw_terceiros_drone_*` e `dim_talhoes`. Com o passo 3, pode usar RPC `api_talhoes_geojson()` para polígonos.

## Permissões — o que NÃO precisa

- Não precisa “entrar na sua conta GitHub” manualmente: o agente já publica no repo autorizado.
- Não dá para o agente abrir Streamlit/Lovable no seu login — só você ajusta Secrets/Reboot lá.
- **Não** envie senha no chat; use **GitHub Secret** ou **Streamlit Secrets**.

## Permissões úteis para o agente (Cursor)

Se quiser que **este chat** rode a carga no futuro: em **Cursor → Environment / Secrets** do projeto, adicione `SUPABASE_DB_URL` (mesmo valor). Aí peça: “rode carga KML”.
