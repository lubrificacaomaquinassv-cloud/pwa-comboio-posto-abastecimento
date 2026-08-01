# Publicar no Streamlit Cloud (link público)

Painel online gratuito em **https://share.streamlit.io** — leva cerca de 5 minutos.

## Passo a passo

1. Abra **https://share.streamlit.io** e entre com a conta GitHub `lubrificacaomaquinassv-cloud`.

2. Clique em **New app** (Criar app).

3. Preencha:
   | Campo | Valor |
   |-------|-------|
   | Repository | `lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento` |
   | Branch | `main` |
   | Main file path | `ADUBACAO_FLORESTAL_2026/app.py` |

4. Clique em **Advanced settings** e confirme:
   - **Python version:** 3.12
   - O arquivo `packages.txt` na pasta do app instala GDAL/GEOS (necessário para GeoPandas).

5. Clique em **Deploy**.

6. Aguarde o build (3–8 min na primeira vez). Quando ficar verde, o link será algo como:
   ```
   https://pwa-comboio-posto-abastecimento-xxxx.streamlit.app
   ```
   (o sufixo é gerado automaticamente; você pode renomear em **Settings → App URL**.)

## Usar os dados reais na nuvem

No servidor **não existem** os arquivos `D:\...`. Na barra lateral do app publicado:

1. Selecione **Enviar arquivos (nuvem)**.
2. Faça upload de:
   - `Adubação de Cobertura .xlsx`
   - `Adubação de Base 2026.xlsx`
   - `fazenda_santa_virginia_completo.kml`
3. Clique em **Recarregar dados**.

Os uploads ficam na sessão atual (não são salvos permanentemente no GitHub).

## Alternativa: dados fixos no repositório

Se quiser que o app online já abra com dados reais **sem upload**:

1. Copie os 3 arquivos para `ADUBACAO_FLORESTAL_2026/data/producao/`
2. Faça commit e push (o KML pode ser grande — considere Git LFS se passar de 50 MB).
3. Ajuste `config.py` ou use variáveis de ambiente no Streamlit Cloud (**Settings → Secrets**):

```toml
ADUBACAO_COBERTURA = "data/producao/cobertura.xlsx"
ADUBACAO_BASE = "data/producao/base.xlsx"
ADUBACAO_KML = "data/producao/fazenda.kml"
```

## Privacidade

Apps no plano gratuito do Streamlit Cloud são **públicos** (qualquer pessoa com o link acessa). Para restringir acesso, use o plano Team ou publique em servidor interno da fazenda.

## Atualizar o app online

Basta dar **push na branch `main`**. O Streamlit Cloud redeploya automaticamente.
