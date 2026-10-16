"""Regras de ciclo de fatura do cartão (fechamento e vencimento)."""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Tuple


def add_months(d: date, months: int) -> date:
    """Soma meses mantendo o dia, ajustando para o último dia do mês se necessário."""
    y, m = d.year, d.month + months
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    last = monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def _mes_ano_fechamento(data_compra: date, dia_fechamento: int) -> Tuple[int, int]:
    if data_compra.day <= dia_fechamento:
        return data_compra.month, data_compra.year
    prox = add_months(date(data_compra.year, data_compra.month, 1), 1)
    return prox.month, prox.year


def data_pagamento_fatura(
    data_compra: date,
    dia_fechamento: int = 22,
    dia_pagamento: int = 4,
    forcar_proximo_ciclo: bool = False,
) -> date:
    """
    Compra até dia_fechamento do mês M → fatura paga no dia_pagamento do mês M+1.
    Compra a partir do dia seguinte ao fechamento → paga no dia_pagamento de M+2.
    forcar_proximo_ciclo: empurra a despesa para o ciclo seguinte (útil no fechamento).
    """
    mes_fechamento, ano_fechamento = _mes_ano_fechamento(data_compra, dia_fechamento)
    if forcar_proximo_ciclo:
        mes_fechamento, ano_fechamento = _mes_ano_fechamento(
            add_months(date(ano_fechamento, mes_fechamento, dia_fechamento), 1),
            dia_fechamento,
        )

    mes_pag = mes_fechamento + 1
    ano_pag = ano_fechamento
    if mes_pag > 12:
        mes_pag = 1
        ano_pag += 1
    last = monthrange(ano_pag, mes_pag)[1]
    return date(ano_pag, mes_pag, min(dia_pagamento, last))


def pagamento_parcela(
    data_compra: date,
    numero_parcela: int,
    dia_fechamento: int = 22,
    dia_pagamento: int = 4,
    forcar_proximo_ciclo: bool = False,
) -> date:
    """Data de pagamento da parcela N (1-based), avançando um ciclo por parcela."""
    ref = add_months(data_compra, numero_parcela - 1)
    return data_pagamento_fatura(
        ref, dia_fechamento, dia_pagamento, forcar_proximo_ciclo=forcar_proximo_ciclo and numero_parcela == 1
    )


def data_fechamento_ciclo(mes_fechamento: int, ano_fechamento: int, dia_fechamento: int) -> date:
    last = monthrange(ano_fechamento, mes_fechamento)[1]
    return date(ano_fechamento, mes_fechamento, min(dia_fechamento, last))


def ciclo_vigente(
    hoje: date,
    dia_fechamento: int = 22,
    dia_pagamento: int = 4,
) -> dict:
    """Ciclo de compras em aberto e datas de fechamento/vencimento."""
    mes_fech, ano_fech = _mes_ano_fechamento(hoje, dia_fechamento)
    fechamento = data_fechamento_ciclo(mes_fech, ano_fech, dia_fechamento)
    vencimento = data_pagamento_fatura(hoje, dia_fechamento, dia_pagamento)
    inicio, _ = periodo_fechamento_para_pagamento(vencimento, dia_fechamento, dia_pagamento)
    ja_fechou = hoje > fechamento
    prox_fech = data_fechamento_ciclo(
        *(_mes_ano_fechamento(add_months(fechamento, 1), dia_fechamento)),
        dia_fechamento,
    )
    prox_venc = add_months(vencimento, 1)
    return {
        "inicio_compras": inicio,
        "fechamento": fechamento,
        "vencimento": vencimento,
        "ja_fechou": ja_fechou,
        "proximo_fechamento": prox_fech,
        "proximo_vencimento": prox_venc,
    }


def periodo_fechamento_para_pagamento(
    data_pagamento: date,
    dia_fechamento: int = 22,
    dia_pagamento: int = 4,
) -> Tuple[date, date]:
    """
    Intervalo de compras (início e fim inclusive) que compõem a fatura paga em data_pagamento.
    """
    if data_pagamento.day != min(dia_pagamento, monthrange(data_pagamento.year, data_pagamento.month)[1]):
        pass
    mes_fech = data_pagamento.month - 1
    ano_fech = data_pagamento.year
    if mes_fech < 1:
        mes_fech = 12
        ano_fech -= 1

    fim = date(ano_fech, mes_fech, dia_fechamento)
    inicio_mes = mes_fech - 1
    inicio_ano = ano_fech
    if inicio_mes < 1:
        inicio_mes = 12
        inicio_ano -= 1
    inicio = date(inicio_ano, inicio_mes, dia_fechamento + 1)
    return inicio, fim


def chave_fatura(data_pagamento: date) -> str:
    """Identificador estável da fatura (data de pagamento ISO)."""
    return data_pagamento.isoformat()
