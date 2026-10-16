# Controle orçamentário doméstico

Painel **Streamlit** + **SQLite** (arquivo local `data/orcamento.db`). Sem Supabase.

## Regra do cartão (padrão)

- Fechamento dia **22**; pagamento dia **4** do mês seguinte ao fechamento.
- Compras até o fechamento entram na fatura com vencimento no mês seguinte.
- Compras após o fechamento entram na fatura seguinte.
- Opção **Próximo ciclo** no lançamento força a despesa para a fatura posterior.

## Baixar no seu PC (Windows)

O projeto **não** fica em `C:\Users\hmauricio` sozinho — você precisa clonar do GitHub **uma vez**:

```powershell
cd $HOME
git clone -b cursor/controle-orcamento-domestico-93ab https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento.git orcamento-casa
cd orcamento-casa\controle_orcamento_domestico
```

Depois, **sempre** entre nesta pasta antes de rodar comandos:

`C:\Users\hmauricio\orcamento-casa\controle_orcamento_domestico`

**Forma mais fácil:** dê dois cliques em `RODAR_APP.bat` (cria `.venv`, instala dependências e abre o painel).

**Porta 8502** — evita conflito com o módulo *Importação de Saídas* (SAP), que costuma usar **8501**.  
Se abrir a tela errada, feche abas antigas de `localhost:8501` e use **http://localhost:8502** (título: *Orçamento Doméstico*).

**Manual:**

```powershell
cd $HOME\orcamento-casa\controle_orcamento_domestico
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Se o PowerShell bloquear o script de activate, use o `.bat` acima ou:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Quando o PR for mergeado na `main`, pode clonar só a branch `main` e usar a mesma subpasta `controle_orcamento_domestico`.

## Executar (Linux / Mac)

```bash
cd controle_orcamento_domestico
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Repositório separado

Para usar só este projeto no seu GitHub pessoal:

```bash
cd controle_orcamento_domestico
git init
git add .
git commit -m "Controle orçamentário doméstico Streamlit + SQLite"
git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
git push -u origin main
```

Não commite `data/orcamento.db` (já está no `.gitignore`).

## Backup no pendrive (sem encher o drive)

**Não copie a pasta inteira** — a subpasta `.venv` tem centenas de MB.

Copie **só**:

```
data\orcamento.db
```

Ou dê dois cliques em **`BACKUP_DADOS.bat`** (grava em `E:\backup-orcamento` por padrão; ou arraste o `.bat` e passe a letra do pendrive).

Para **restaurar** em outro PC ou depois de reinstalar: coloque `orcamento.db` de volta em `data\` dentro de `orcamento-casa` e rode `RODAR_APP.bat`.
