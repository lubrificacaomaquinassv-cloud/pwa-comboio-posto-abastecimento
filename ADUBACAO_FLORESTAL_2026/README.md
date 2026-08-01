# Adubação Florestal 2026 — Fazenda Santa Virgínia

Painel operacional de **silvicultura / silvipastoril** (cobertura, base, mapa GIS, NPK).

**Link oficial:** https://adubacao-florestal-sv.streamlit.app

## Streamlit Cloud

| Campo | Valor |
|-------|-------|
| App | `adubacao-florestal-sv` |
| Branch | `main` |
| Main file | `ADUBACAO_FLORESTAL_2026/app.py` |

> O código pode ficar temporariamente no repositório interno da organização.
> O **nome que a gerência vê** é o link acima — não aparece “posto” ou “abastecimento”.

## Repositório dedicado (recomendado)

Para credibilidade institucional, crie no GitHub:

`lubrificacaomaquinassv-cloud/adubacao-florestal-sv`

Copie **todo o conteúdo desta pasta** para a raiz do novo repo e aponte o Streamlit Cloud para `app.py`.

## PC local

```bat
cd ADUBACAO_FLORESTAL_2026
py -m pip install -r requirements.txt
py -m streamlit run app.py
```
