# Desbloqueio — por que o “script 05” trava desde ontem

## O que está errado (não é a pasta DADOS_PAINEL)

| O que você fez | O que o banco tem | Resultado |
|----------------|-------------------|-----------|
| Rodou **`005_api_mapa_talhoes.sql`** várias vezes | **`dim_talhoes`** (Apontamento) = só **cadastro** (código, área) **sem polígono** | 0 geometrias |
| | **`dim_talhao_florestal`** = tabela existe, mas **vazia** (KML nunca gravou) | 0 geometrias |
| Script 005 procura polígonos | Nenhum | **ERRO: Sem poligonos no banco** |

**Conclusão:** os arquivos em `C:\Users\hmauricio\Desktop\DADOS_PAINEL` estão no **lugar certo** para o PC.  
O que **não aconteceu** foi o **Python gravar** KML + planilhas no Supabase (PowerShell na pasta errada / `cd` que falhou).

---

## Por que tantos “projetos” confundem

| Nome | Função |
|------|--------|
| `003` | Tabelas adubação |
| `004` legado | coluna `ativo` |
| **`005_views_lovable_adubacao.sql`** | Lovable lê **adubação** (planilhas) |
| **`005_api_mapa_talhoes.sql`** | Lovable lê **mapa** (precisa polígonos no banco) |
| 004 mapa **obsoleto** | **Não executar** |

Você ficou preso no **005 mapa**, mas o passo que falta é **carga no PC**, não mais SQL.

---

## Saia do loop HOJE (ordem fixa)

### A) Pare de rodar (por enquanto)

- **`005_api_mapa_talhoes.sql`** — só depois que existir polígono no banco.

### B) SQL (uma vez, se ainda faltar)

1. `003_schema_adubacao_florestal.sql` (já feito — “already exists” é normal)
2. `004_controle_projeto_legado.sql`
3. **`005_views_lovable_adubacao.sql`** (adubação Lovable + painel)

### C) Carga no PC (obrigatório)

**IMPORTANTE:** no GitHub, a pasta `adubacao-florestal-sv-streamlit` **só existe no branch** `cursor/finalizar-adubacao-dados-fbe9`, **não** no `main`. Por isso o `cd ...\adubacao-florestal-sv-streamlit` falhou depois do clone.

```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento.git
cd pwa-comboio-posto-abastecimento
git fetch origin
git checkout cursor/finalizar-adubacao-dados-fbe9
powershell -ExecutionPolicy Bypass -File adubacao-florestal-sv-streamlit\RODAR_CARGA_WINDOWS.ps1
```

(O script pede `SUPABASE_DB_URL` se ainda não estiver definida.)

Isso grava **planilhas** em `fato_adubacao_*` e **KML** em `dim_talhao_florestal.geom`.

### D) Confirme no DBeaver

```sql
SELECT COUNT(*) FROM fato_adubacao_cobertura;
SELECT COUNT(*) FROM dim_talhao_florestal WHERE geom IS NOT NULL;
```

Os dois devem ser **> 0**.

### E) Agora sim (opcional Lovable mapa API)

Execute **`005_api_mapa_talhoes.sql`** de novo → deve dar **NOTICE OK** com N polígonos.

---

## Streamlit sem esperar o 005 mapa

Com **Secrets** `SUPABASE_DB_URL` + origem **Supabase**, o painel lê adubação do banco e pode usar **KML no deploy** — não depende do 005 mapa para funcionar.

---

## Checklist “saí do ponto zero”

- [ ] `COUNT` cobertura > 0  
- [ ] `COUNT` geom talhão > 0  
- [ ] Painel: “X talhões cruzados com o mapa”  
- [ ] (Opcional) 005_api_mapa OK  
