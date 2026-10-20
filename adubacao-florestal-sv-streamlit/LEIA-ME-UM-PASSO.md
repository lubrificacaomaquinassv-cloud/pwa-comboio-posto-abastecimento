# Um único caminho (sem menu escondido no Streamlit)

## Atalho no Windows (duplo clique)

1. Abra a pasta `pwa-comboio-posto-abastecimento\adubacao-florestal-sv-streamlit`
2. Duplo clique em **`ATUALIZAR_E_ABRIR_PAINEL.bat`**

Isso faz `git pull` e abre o painel no navegador (**localhost:8501**).  
**Não digite `S` no PowerShell** — use o `.bat`.

## A) Subir planilhas → Supabase (PowerShell)

Na pasta do projeto clonado:

```powershell
cd $env:USERPROFILE\Desktop\pwa-comboio-posto-abastecimento
git checkout cursor/adubacao-supabase-mapa-fbe9
git pull origin cursor/adubacao-supabase-mapa-fbe9
powershell -ExecutionPolicy Bypass -File adubacao-florestal-sv-streamlit\RODAR_CARGA_WINDOWS.ps1
```

## B) Atualizar o painel na internet

**Você NÃO precisa mudar branch no site share.streamlit.io** se o app já foi criado na branch  
`cursor/adubacao-supabase-mapa-fbe9` (é o padrão deste projeto).

Quando o GitHub recebe código novo nessa branch, o Streamlit **redeploy sozinho**.

No PC, só confira que está na branch certa:

```powershell
powershell -ExecutionPolicy Bypass -File adubacao-florestal-sv-streamlit\PUBLICAR_PAINEL_AUTOMATICO.ps1
```

Depois de **2 a 5 minutos**, abra o painel e veja na **barra lateral esquerda**:

**Versão do painel: 2026.10.20-mapa-ficha-v3**

## C) Ver adubação de um talhão

1. Barra lateral → **Ver talhão** → escolha o número  
2. Aba **Mapa** → role até **Ficha do talhão**

O clique no mapa pode falhar; a lista na lateral **sempre funciona**.
