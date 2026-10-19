# Publicar o painel (configuração mais simples)

## Streamlit Cloud — só 3 campos

1. Abra o link do app → canto inferior direito **Manage app** (Gerenciar app).
2. Menu lateral **Settings** (ícone de engrenagem).
3. Seção **General** → **App**:

| Campo | Valor |
|--------|--------|
| **Repository** | `lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento` |
| **Branch** | `adubacao-florestal-sv` |
| **Main file path** | `app.py` |

4. **Secrets** (mesma tela, aba Secrets):

```toml
SUPABASE_DB_URL = "postgresql+psycopg://postgres.SEU_REF:SUA_SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
SUPABASE_GIS_TABLE = "dim_talhoes"
```

5. **Save** → volte ao app → **⋮** → **Reboot app**.

**Funcionou** se aparecer **☁️ Supabase (oficial)** e **GIS Supabase: public.dim_talhoes**.

---

## Onde fica “Manage app”?

Na página do painel aberto no navegador, **canto inferior direito** — link **Manage app**.  
Não é aba do painel; é o **painel de administração** do Streamlit Cloud.

---

## Dados de adubação (planilhas)

PowerShell, uma vez:

```powershell
git clone https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento.git
cd pwa-comboio-posto-abastecimento
git checkout adubacao-florestal-sv
powershell -ExecutionPolicy Bypass -File scripts\CARGA_DADOS_PAINEL.ps1
```

SQL no Supabase (uma vez): `sql/003_schema_adubacao_florestal.sql`
