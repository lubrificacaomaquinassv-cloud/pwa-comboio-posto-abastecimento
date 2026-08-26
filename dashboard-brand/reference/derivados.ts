/**
 * SUBSTITUIR o conteúdo de src/lib/derivados.ts (ou equivalente) no projeto Lovable.
 * Troca horas_efetivas → horasMaquina em disponibilidade e combustível.
 */
import { useMemo } from "react";
import { useApontamentos, useOsParada, useAbastecimento } from "@/hooks/agro"; // ajuste o path se necessário
import { horasMaquina, parseNum } from "@/lib/horas-maquina"; // ou ./horas-maquina

function uniqueFrotas(ids: Array<string | null | undefined>): string[] {
  return [...new Set(ids.map((id) => String(id ?? "").trim()).filter(Boolean))];
}

/** Disponibilidade por trator — horas operando = horasMaquina (horímetro). */
export function useDisponibilidadePorFrota() {
  const { data: apont = [] } = useApontamentos();
  const { data: os = [] } = useOsParada();

  return useMemo(() => {
    const ids = uniqueFrotas([
      ...apont.map((r) => r.id_frota),
      ...os.map((r) => r.id_frota),
    ]);

    return ids.map((id_frota) => {
      const horas_operando = apont
        .filter((r) => r.id_frota === id_frota)
        .reduce((sum, r) => sum + horasMaquina(r), 0);

      const osFrota = os.filter((r) => r.id_frota === id_frota);
      const horas_parada = osFrota.reduce(
        (sum, r) => sum + parseNum(r.horas_parada),
        0
      );

      const total = horas_operando + horas_parada;

      return {
        mes_key: null as string | null,
        id_frota,
        horas_operando,
        horas_parada,
        qtd_os: osFrota.length,
        disponibilidade_pct: total > 0 ? (horas_operando / total) * 100 : null,
      };
    });
  }, [apont, os]);
}

/** Diesel por trator — L/h = litros_total / horasMaquina (horímetro). */
export function useCombustivelPorFrota() {
  const { data: apont = [] } = useApontamentos();
  const { data: abast = [] } = useAbastecimento();

  return useMemo(() => {
    const ids = uniqueFrotas(abast.map((r) => r.id_frota));

    return ids.map((id_frota) => {
      const abastFrota = abast.filter((r) => r.id_frota === id_frota);
      const litros_total = abastFrota.reduce(
        (sum, r) => sum + parseNum(r.litros),
        0
      );
      const litros_posto = abastFrota
        .filter((r) => (r.origem ?? "").toLowerCase().includes("posto"))
        .reduce((sum, r) => sum + parseNum(r.litros), 0);

      const horas_operando = apont
        .filter((r) => r.id_frota === id_frota)
        .reduce((sum, r) => sum + horasMaquina(r), 0);

      return {
        mes_key: null as string | null,
        id_frota,
        horas_operando,
        litros_total,
        litros_posto,
        litros_comboio: litros_total - litros_posto,
        litros_por_hora: horas_operando > 0 ? litros_total / horas_operando : null,
      };
    });
  }, [apont, abast]);
}
