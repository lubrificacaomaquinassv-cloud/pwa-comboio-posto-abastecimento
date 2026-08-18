/**
 * Métrica oficial de horas-máquina para todos os KPIs do painel.
 * Usar em derivados, disponibilidade, L/h e gráficos — NÃO usar horas_efetivas diretamente.
 */
export function parseNum(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

export type ApontamentoHoras = {
  horas_horimetro?: number | string | null;
  horas_efetivas?: number | string | null;
  horas_operacao_calc?: number | string | null;
};

/** Prioriza horímetro; fallback para horas calculadas. */
export function horasMaquina(row: ApontamentoHoras): number {
  const horimetro = parseNum(row.horas_horimetro);
  if (horimetro > 0) return horimetro;
  return parseNum(row.horas_efetivas) || parseNum(row.horas_operacao_calc);
}
