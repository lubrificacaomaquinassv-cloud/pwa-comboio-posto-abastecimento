# Atualizar o painel na internet (Streamlit Cloud)

O comando **`git pull` no seu PC não altera o site**  
`https://adubacao-florestal-sv-hbqqrye72rwfhhcjprayxy.streamlit.app/`  
Esse site lê o código **direto do GitHub**, na branch configurada no Streamlit Cloud.

## Passo a passo

1. Abra https://share.streamlit.io e entre com GitHub.
2. Abra o app **Adubação Florestal**.
3. **Settings** (⚙️):
   - **Repository:** `lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento`  
     (ou `adubacao-florestal-sv` se for esse o repo ligado ao app)
   - **Branch:** `cursor/finalizar-adubacao-dados-fbe9`
   - **Main file:** `adubacao-florestal-sv-streamlit/app.py`
4. **Save** → **Redeploy** (ou “Reboot app”).
5. Abra o painel e confira na **barra lateral esquerda**:
   - **Versão do painel: 2026.10.20-mapa-ficha-v3**
   - Menu **📍 Ver talhão**

Se a versão for antiga (`2026.10.20-dados-adubacao-final` ou outra), o site ainda não está na branch certa.

## Testar no PC (opcional)

```powershell
cd $env:USERPROFILE\Desktop\pwa-comboio-posto-abastecimento\adubacao-florestal-sv-streamlit
git pull origin cursor/finalizar-adubacao-dados-fbe9
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Abra o endereço local que o terminal mostrar (geralmente http://localhost:8501).
