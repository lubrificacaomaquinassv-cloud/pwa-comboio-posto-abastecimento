# O que fazer agora (projeto não finalizado)

Seu mapa **já abre** (KML). Falta **levar a planilha de Cobertura para o Supabase** e o Streamlit ler de lá.

A pasta correta no seu PC:

`C:\Users\hmauricio\Desktop\DADOS_PAINEL`

---

## Passo 1 — Conferir planilhas (SEM banco, não falha por senha)

1. Abra **PowerShell**.
2. Vá na pasta do projeto (onde está `app.py`), por exemplo:

```powershell
cd C:\Users\hmauricio\Desktop\pwa-adubacao\adubacao-florestal-sv-streamlit
```

(Se o clone estiver em outro lugar, use a pasta que contém `scripts\`.)

3. Rode **só isto**:

```powershell
python scripts/conferir_planilhas_local.py "C:\Users\hmauricio\Desktop\DADOS_PAINEL"
```

**Deve aparecer:** quantidade de lançamentos e **“Talhões em COMUM” > 0**.  
Se der **0 em comum**, o painel continuará 0% — problema nos arquivos, não no Streamlit.

---

## Passo 2 — SQL no Supabase (site, uma vez)

1. https://supabase.com → seu projeto → **SQL Editor**
2. Cole e execute o arquivo **`sql/003_schema_adubacao_florestal.sql`**
3. (Opcional, projeto antigo no banco) **`sql/004_controle_projeto_legado.sql`**

---

## Passo 3 — Subir planilhas → Supabase

**Uma linha por vez.** Cole a URL real (senha **Database**, usuário `postgres.azhpxhrwhegfysoeqmft`):

```powershell
$env:SUPABASE_DB_URL = "postgresql+psycopg://postgres.azhpxhrwhegfysoeqmft:SUA_SENHA_AQUI@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
```

Depois:

```powershell
python scripts/analisar_e_sync_adubacao.py --dados-dir "C:\Users\hmauricio\Desktop\DADOS_PAINEL" --sync --modo por_talhao
```

Ou:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\CARGA_DADOS_PAINEL.ps1
```

**Sucesso:** mensagem com linhas gravadas. No Supabase → **Table Editor** → `fato_adubacao_cobertura` com registros.

**Erro de senha:** refaça o Passo 3 com a senha do painel Database (Settings → Database).

---

## Passo 4 — Streamlit Cloud

1. **Secrets:** mesma `SUPABASE_DB_URL` **ou** `SUPABASE_URL` + `SUPABASE_KEY`
2. Branch com código novo (ex.: `cursor/finalizar-adubacao-dados-fbe9`)
3. Main file: `adubacao-florestal-sv-streamlit/app.py`
4. **Reboot app**
5. Sidebar: **☁️ Supabase (oficial)**

Deve aparecer texto do tipo **“X talhões cruzados com o mapa”** (X > 0).

---

## Sobre o aviso “30 códigos em mais de uma classe”

Isso é do **KML** (mesmo número em classes diferentes). **Não impede** a carga da planilha. O coordenador pode revisar depois.

---

## Sobre a ficha “Clique em um polígono…”

Depois do Passo 3 + 4, clique de novo no talhão. Se ainda vazio, confira se o build na sidebar é **`2026.10.20-dados-adubacao-final`** ou mais novo.
