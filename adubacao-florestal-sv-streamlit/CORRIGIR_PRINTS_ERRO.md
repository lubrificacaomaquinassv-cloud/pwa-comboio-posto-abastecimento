# O que falhou nos seus dois prints

## Print 1 — DBeaver / SQL

**Erro:** `column "ativo" does not exist`

| Causa | Quem |
|--------|------|
| A consulta usa a coluna **`ativo`**, que só existe depois do arquivo **`sql/004_controle_projeto_legado.sql`**. | Instrução nossa (assumiu 004 já rodado) |
| Você rodou só o **`003`** (ou carga antiga) — tabela sem `ativo`. | Estado normal do banco |

**O que fazer agora (escolha A ou B):**

**A) Só ver se tem dados (sem 004):** abra `sql/VERIFICAR_DADOS_ADUBACAO.sql` e execute.

**B) Fluxo completo Lovable + legado:**

1. SQL Editor → cole e execute **`sql/004_controle_projeto_legado.sql`**
2. Depois **`sql/005_views_lovable_adubacao.sql`**
3. Aí sim:
   ```sql
   SELECT COUNT(*) FROM fato_adubacao_cobertura WHERE ativo IS DISTINCT FROM FALSE;
   SELECT * FROM vw_api_adubacao_cobertura LIMIT 5;
   ```

Se `COUNT(*)` em `fato_adubacao_cobertura` for **0**, o banco ainda está vazio — falta o **Passo PowerShell** abaixo (carga da pasta DADOS_PAINEL).

---

## Print 2 — PowerShell

**Erros:**

1. `cd ...\pwa-adubacao\adubacao-florestal-sv-streamlit` → **pasta não existe** no seu PC  
   → Você executou certo o caminho que sugerimos, mas **esse clone não está nesse lugar** (ou nunca foi clonado).

2. `git pull` → `not a git repository`  
   → Você estava em `C:\Users\hmauricio`, não dentro do repo.

3. `python scripts\conferir...` → arquivo não encontrado  
   → Python procurou `C:\Users\hmauricio\scripts\...` porque **não entrou na pasta do projeto**.

**Nada disso é falha da planilha** — é **diretório errado**.

### Caminho certo no Windows (copiar linha a linha)

**Se ainda não clonou o GitHub:**

```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento.git
cd pwa-comboio-posto-abastecimento\adubacao-florestal-sv-streamlit
git checkout cursor/finalizar-adubacao-dados-fbe9
pip install -r requirements.txt
```

**Se já clonou em outro lugar**, ache o script:

```powershell
Get-ChildItem -Path $env:USERPROFILE\Desktop -Recurse -Filter "conferir_planilhas_local.py" -ErrorAction SilentlyContinue | Select-Object -First 1 FullName
```

Use a pasta **pai de `scripts`** no próximo `cd` (onde existe `app.py`).

**Conferir planilhas (sem Supabase):**

```powershell
python scripts/conferir_planilhas_local.py "C:\Users\hmauricio\Desktop\DADOS_PAINEL"
```

**Subir para Supabase** (mesma janela, já dentro de `adubacao-florestal-sv-streamlit`):

```powershell
$env:SUPABASE_DB_URL = "postgresql+psycopg://postgres.azhpxhrwhegfysoeqmft:SUA_SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
python scripts/analisar_e_sync_adubacao.py --dados-dir "C:\Users\hmauricio\Desktop\DADOS_PAINEL" --sync --modo por_talhao
```

---

## Segurança

No print aparece a **senha do banco** na URL. Recomendado: Supabase → **Database → Reset database password** e usar a senha nova só no `$env:SUPABASE_DB_URL` (não compartilhar em print/chat).

---

## Resumo

| Problema | Tipo |
|----------|------|
| Coluna `ativo` | SQL 004 não executado — use `VERIFICAR_DADOS_ADUBACAO.sql` ou rode 004+005 |
| Scripts Python | Pasta do projeto errada — clone/checkout acima |
| Painel 0% / sem adubação | Carga ainda não rodou com sucesso → tabela vazia |
