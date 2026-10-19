# Por que o site ainda pede KML / planilhas?

O endereço **https://adubacao-florestal-sv-hbqqrye72rwfhhcjprayxy.streamlit.app/** está ligado ao repositório **`adubacao-florestal-sv`**.  
Enquanto lá estiver só o commit antigo (`f15c1bb`), a tela **não** mostra “☁️ Supabase (oficial)” — só upload de Excel/KML.

## 1. Publicar o código novo no GitHub

Escolha **uma** opção:

### Opção A — Repo oficial (recomendado para esse URL)

No PC, clone ou abra o repo `adubacao-florestal-sv` e copie para a raiz dele o conteúdo da pasta **`adubacao-florestal-sv-streamlit`** deste repositório PWA (branch do PR #5), depois:

```powershell
git add -A
git commit -m "Painel Supabase-first e mapa Esri"
git push origin main
```

### Opção B — Manter código no PWA

No [Streamlit Cloud](https://share.streamlit.io): **Settings** → Repository = `pwa-comboio-posto-abastecimento` → **Main file** = `adubacao-florestal-sv-streamlit/app.py` → Save → **Redeploy**.

## 2. Secret no Streamlit Cloud

**Settings → Secrets:**

```toml
SUPABASE_DB_URL = "postgresql+psycopg://postgres.SEU_REF:SUA_SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
```

(Senha e ref iguais às do Supabase → Project Settings → Database → Connection string, modo **Transaction pooler**, driver **psycopg**.)

## 3. Criar tabelas no Supabase

No **SQL Editor**, execute o arquivo:

`sql/003_schema_adubacao_florestal.sql`

## 4. Mapa GIS no Supabase

Se o **Apontamento de Campo** já carregou o KML, os polígonos estão em **`public.dim_talhoes`**.  
O painel (build `2026.10.19-gis-dim-talhoes`) lê essa tabela **automaticamente** — não precisa subir KML de novo.

Opcional nos Secrets: `SUPABASE_GIS_TABLE = "dim_talhoes"`.

## 5. Enviar planilhas do Desktop (DADOS_PAINEL)

**Não** copie os exemplos com `caminho\do\repo` ou `SEU_ARQUIVO_...` — use o script:

```powershell
cd C:\Users\hmauricio\caminho-real-do-repo\adubacao-florestal-sv
powershell -ExecutionPolicy Bypass -File scripts\CARGA_DADOS_PAINEL.ps1
```

O script usa `Desktop\DADOS_PAINEL`, acha o `.kml` e os `.xlsx` sozinho e pede a URL do banco se ainda não existir.

## 6. Conferir se o deploy funcionou

Abra o painel: na barra lateral deve aparecer **“☁️ Supabase (oficial)”**, mensagem **GIS Supabase: public.dim_talhoes** e build **`2026.10.19-gis-dim-talhoes`**.  
Se não aparecer, o Streamlit ainda está no commit antigo — repita o passo 1 e **Redeploy**.
