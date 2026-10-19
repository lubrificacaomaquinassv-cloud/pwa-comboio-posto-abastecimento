# Painel não abre? Siga só estes 4 passos

Você vê **“Mapa KML não encontrado”** porque o Streamlit Cloud ainda está com **código antigo** (antes do Supabase e do GIS `dim_talhoes`).  
Não é falta de KML no Supabase — é o **deploy** que não foi atualizado.

---

## Passo 1 — Ajustar o app no Streamlit Cloud (5 min)

1. Abra https://share.streamlit.io e entre com GitHub.
2. Clique no app **adubacao-florestal-sv** (ou o que aponta para esse URL).
3. Menu **⋮** → **Settings** (Gerenciar app).

Preencha **exatamente**:

| Campo | Valor |
|--------|--------|
| **Repository** | `lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento` |
| **Branch** | `cursor/adubacao-supabase-mapa-fbe9` |
| **Main file path** | `adubacao-florestal-sv-streamlit/app.py` |

4. Aba **Secrets** → cole (com sua senha e ref reais):

```toml
SUPABASE_DB_URL = "postgresql+psycopg://postgres.SEU_REF:SUA_SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
SUPABASE_GIS_TABLE = "dim_talhoes"
```

(A URL está em Supabase → Project Settings → Database → **Transaction pooler** → URI, trocando `postgresql://` por `postgresql+psycopg://`.)

5. **Save** → **Reboot app** / **Redeploy**.

### Como saber que deu certo

Na barra lateral do painel deve aparecer:

- **☁️ Supabase (oficial)**
- **GIS Supabase: public.dim_talhoes (… polígonos)**
- Build **`2026.10.19-gis-dim-talhoes`**

Se ainda aparecer só upload de Excel/KML e a mensagem de KML, o Passo 1 não foi salvo ou o redeploy não rodou.

---

## Passo 2 — Tabelas de adubação no Supabase (uma vez)

No Supabase → **SQL Editor**, execute o arquivo:

`adubacao-florestal-sv-streamlit/sql/003_schema_adubacao_florestal.sql`

(Isso cria `fato_adubacao_cobertura`, etc. O **mapa** continua vindo de `dim_talhoes`, que você já tem.)

---

## Passo 3 — Subir as planilhas da pasta DADOS_PAINEL (uma vez)

No **PowerShell**, na pasta do projeto clonado do GitHub (não use `caminho\do\repo`):

```powershell
git clone https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento.git
cd pwa-comboio-posto-abastecimento
git checkout cursor/adubacao-supabase-mapa-fbe9
powershell -ExecutionPolicy Bypass -File adubacao-florestal-sv-streamlit\scripts\CARGA_DADOS_PAINEL.ps1
```

O script usa `Desktop\DADOS_PAINEL`, acha os `.xlsx` e **não exige KML** se o GIS já está no Supabase.

---

## Passo 4 — Abrir o painel

https://adubacao-florestal-sv-hbqqrye72rwfhhcjprayxy.streamlit.app/

Aba **Mapa** → clique no talhão → ficha lateral com adubação e **Realizado = Total gasto ÷ Floresta (há)**.

---

## Alternativa (se quiser manter o repo `adubacao-florestal-sv`)

Copie todo o conteúdo da pasta `adubacao-florestal-sv-streamlit` para a **raiz** do repo `adubacao-florestal-sv`, faça `git push origin main`, e no Streamlit use **Repository** = `adubacao-florestal-sv`, **Main file** = `app.py`, mesma branch `main` + Secrets do Passo 1.

---

## O que NÃO fazer

- Não colar no PowerShell textos de exemplo (`SEU_ARQUIVO`, `caminho\do\repo`, `SEU_REF` sem trocar).
- Não esperar o mapa no site antigo sem redeploy — ele **nunca** lerá `dim_talhoes` sozinho.
