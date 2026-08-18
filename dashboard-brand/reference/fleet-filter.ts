/**
 * Filtro oficial de frota — Painéis Santa Virgínia
 * Escopo atual: TRATORES (horas-máquina), sem caminhões, veículos ou terceiros.
 *
 * Fonte de verdade: dim_frota (Supabase)
 * Abastecimento: comboio_v2 + posto (via vw_prod_abastecimento_base)
 */

export type EscopoFrota = "TRATORES" | "TODA_FROTA";

const norm = (value: unknown) => String(value ?? "").trim().toUpperCase();

/** Terceiros conhecidos — não pertencem à frota própria da fazenda. */
export const FROTAS_TERCEIRAS = new Set([
  "920K",
  "920 K",
]);

/** Categorias sempre excluídas dos painéis de horas-máquina. */
export const CATEGORIAS_EXCLUIDAS = new Set([
  "CAMINHAO",
  "MOTO",
  "VEICULO LEVE",
  "TERCEIRO",
  "IMPLEMENTO",
]);

export type DimFrota = {
  id_frota: string;
  modelo?: string | null;
  categoria?: string | null;
  tipo?: string | null;
};

export function isTrator(row: DimFrota): boolean {
  const modelo = norm(row.modelo);
  const categoria = norm(row.categoria);
  return modelo.includes("TRATOR") || (categoria === "MAQUINA" && modelo.includes("TRATOR"));
}

export function isTerceiro(idFrota: string): boolean {
  return FROTAS_TERCEIRAS.has(norm(idFrota));
}

export function isCategoriaExcluida(categoria: string | null | undefined): boolean {
  return CATEGORIAS_EXCLUIDAS.has(norm(categoria));
}

/**
 * Monta o conjunto de frotas válidas para o escopo TRATORES.
 * Inclui apenas tratores cadastrados em dim_frota.
 */
export function buildFrotasTratores(dimFrota: DimFrota[]): Set<string> {
  const set = new Set<string>();
  for (const row of dimFrota) {
    const id = norm(row.id_frota);
    if (!id || isTerceiro(id) || isCategoriaExcluida(row.categoria)) continue;
    if (isTrator(row)) set.add(id);
  }
  return set;
}

/** Compatível com o filtro Ys() do painel Lovable. */
export function filterByEscopo<T extends { id_frota?: string; frota?: string }>(
  rows: T[],
  escopo: EscopoFrota,
  frotasTratores: Set<string>
): T[] {
  if (escopo !== "TRATORES" || frotasTratores.size === 0) return rows;
  return rows.filter((row) => {
    const id = norm(row.id_frota ?? row.frota);
    return id && frotasTratores.has(id) && !isTerceiro(id);
  });
}

/** IDs de tratores ativos hoje (18 unidades). Gerado a partir de dim_frota. */
export const TRATORES_IDS = [
  "3014", "3019", "3281", "3283", "3305", "3306", "3307",
  "3336", "3337", "3350", "3363", "3368", "3369",
  "3380", "3393", "3394", "3396", "3402",
] as const;
