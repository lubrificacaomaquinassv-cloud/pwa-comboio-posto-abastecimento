# Como publicar este projeto no GitHub (igual aos outros painéis SV)

Repositório alvo: **`lubrificacaomaquinassv-cloud/adubacao-florestal-sv`**

---

## Opção A — Pelo site GitHub (subir arquivo por arquivo)

1. Acesse https://github.com/organizations/lubrificacaomaquinassv-cloud/repositories/new  
   (precisa estar logado na conta da organização)

2. Nome do repositório: **`adubacao-florestal-sv`**

3. Marque **Public** → **Create repository**

4. Clique em **"uploading an existing file"**

5. Arraste **todos os arquivos desta pasta** mantendo as pastas:
   - Raiz: `app.py`, `config.py`, `etl.py`, `npk.py`, `ui.py`, `requirements.txt`, `packages.txt`, `.gitignore`, `README.md`
   - Pasta `.streamlit/` → arquivo `config.toml`
   - Pasta `data/sample/` → `cobertura.xlsx`, `base.xlsx`, `talhoes.geojson`

6. Commit: **"Painel Adubação Florestal 2026"**

7. No **Streamlit Cloud** (https://share.streamlit.io):
   - Novo app → repo `adubacao-florestal-sv` → main file **`app.py`**
   - URL: `adubacao-florestal-sv.streamlit.app`

---

## Opção B — Pelo PC (mais rápido, recomendado)

1. Copie a pasta **`adubacao-florestal-sv`** para o seu PC  
   (ex.: `C:\adubacao-florestal-sv`)

2. Crie o repositório vazio no GitHub (passo 1–3 acima)

3. Abra o Prompt de Comando **dentro da pasta** e rode:

```bat
git init
git add .
git commit -m "Painel Adubação Florestal 2026 — Santa Virgínia"
git branch -M main
git remote add origin https://github.com/lubrificacaomaquinassv-cloud/adubacao-florestal-sv.git
git push -u origin main
```

4. Configure o Streamlit Cloud apontando para **`app.py`**

---

## Opção C — Branch pronta (se o repositório ainda não existir)

No repositório `pwa-comboio-posto-abastecimento` já existe a branch **`adubacao-florestal-sv`**
com estes arquivos na raiz. Depois que alguém da org criar o repo vazio:

```bat
git clone -b adubacao-florestal-sv --single-branch https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento.git temp-sv
cd temp-sv
git remote set-url origin https://github.com/lubrificacaomaquinassv-cloud/adubacao-florestal-sv.git
git push -u origin main
```

---

## Lista de arquivos (checklist)

```
app.py
config.py
etl.py
npk.py
ui.py
requirements.txt
packages.txt
.gitignore
README.md
.streamlit/config.toml
data/sample/cobertura.xlsx
data/sample/base.xlsx
data/sample/talhoes.geojson
```
