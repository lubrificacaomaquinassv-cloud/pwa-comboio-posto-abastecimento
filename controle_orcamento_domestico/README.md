# Controle orçamentário doméstico

Painel **Streamlit** + **SQLite** (arquivo local `data/orcamento.db`). Sem Supabase.

## Regra do cartão (padrão)

- Fechamento dia **22**; pagamento dia **4** do mês seguinte ao fechamento.
- Compras até o fechamento entram na fatura com vencimento no mês seguinte.
- Compras após o fechamento entram na fatura seguinte.
- Opção **Próximo ciclo** no lançamento força a despesa para a fatura posterior.

## Executar

```bash
cd controle_orcamento_domestico
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
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
