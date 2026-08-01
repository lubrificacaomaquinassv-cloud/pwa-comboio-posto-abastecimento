# Adubação Florestal 2026

Painel Streamlit — Fazenda Santa Virgínia.

## Streamlit Cloud

| Campo | Valor |
|-------|-------|
| Repositório | `lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento` |
| Branch | `main` |
| Main file | `ADUBACAO_FLORESTAL_2026/app.py` |

## Arquivos

```
ADUBACAO_FLORESTAL_2026/
  app.py          ← entrada
  config.py       ← caminhos D:\
  etl.py          ← planilhas + KML
  npk.py          ← calculadora
  ui.py           ← visual SV
  requirements.txt
  packages.txt
  data/sample/    ← demo
```

## PC local

```bat
cd ADUBACAO_FLORESTAL_2026
py -m pip install -r requirements.txt
py -m streamlit run app.py
```
