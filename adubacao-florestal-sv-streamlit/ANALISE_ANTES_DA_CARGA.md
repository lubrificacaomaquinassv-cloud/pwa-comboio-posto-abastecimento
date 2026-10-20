# Análise antes da carga (projeto anterior no Supabase)

## Situação

O Supabase pode conter lançamentos do **projeto de adubação anterior**.  
As planilhas atuais em `Desktop\DADOS_PAINEL` são a **fonte oficial** da operação Santa Virgínia **agora**.

**Não apagamos** o histórico antigo: marcamos como **inativo** o que foi substituído nos talhões que aparecem na planilha atual.

## Passo 0 — SQL (uma vez)

No Supabase → SQL Editor:

1. `sql/003_schema_adubacao_florestal.sql` (se ainda não rodou)
2. **`sql/004_controle_projeto_legado.sql`** (colunas `projeto_carga`, `ativo`, views de auditoria)

Ver legado:

```sql
SELECT * FROM vw_auditoria_cobertura_por_projeto;
```

## Passo 1 — Só analisar (sem gravar)

```powershell
cd adubacao-florestal-sv-streamlit
$env:SUPABASE_DB_URL = "postgresql+psycopg://..."
python scripts/analisar_e_sync_adubacao.py --dados-dir "$env:USERPROFILE\Desktop\DADOS_PAINEL" --analise-only
```

O JSON mostra:

| Campo | Significado |
|--------|-------------|
| `novos_na_planilha` | Chaves que não existem no Supabase |
| `alterados` | Mesma chave, área/dose/operador diferente |
| `iguais` | Já está igual — **não será regravado** |
| `so_no_supabase` | Só no banco (projeto anterior ou carga antiga) |
| `supabase_por_arquivo_origem` | De qual carga veio cada bloco |
| `talhoes_so_legado_supabase` | Talhões só no banco e **não** na planilha atual (permanecem até você decidir) |

Revise `amostra_alterados` e `amostra_so_supabase` antes do sync.

## Passo 2 — Subir só o atualizado

Modo recomendado (**por talhão**):

- Grava **novos + alterados**
- Nos talhões que estão na planilha, **desativa** lançamentos antigos que não existem mais na planilha
- Talhões que existem **só** no projeto anterior **não são apagados** (continuam `ativo=true` até migrar ou desativar manualmente)

```powershell
python scripts/analisar_e_sync_adubacao.py --dados-dir "$env:USERPROFILE\Desktop\DADOS_PAINEL" --sync --modo por_talhao --projeto sv_florestal_2026
```

`CARGA_DADOS_PAINEL.ps1` usa o mesmo sync inteligente por padrão.

## Passo 3 — Confirmar

```sql
SELECT * FROM vw_auditoria_cobertura_por_projeto;
SELECT COUNT(*) FROM fato_adubacao_cobertura WHERE ativo = TRUE;
```

Painel Streamlit (origem ☁️ Supabase) lê **apenas `ativo = TRUE`**.

## Se quiser esconder TODO o legado

Só depois de validar a planilha:

```sql
UPDATE fato_adubacao_cobertura
SET ativo = FALSE
WHERE COALESCE(projeto_carga, 'legado') <> 'sv_florestal_2026'
  AND ativo = TRUE;
```

(Ajuste o nome do projeto se usou outro em `--projeto`.)
