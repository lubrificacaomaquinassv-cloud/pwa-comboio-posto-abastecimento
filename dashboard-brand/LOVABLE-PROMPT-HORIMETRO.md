# Prompt Lovable — Unificar métrica horímetro (item 1)

Copie **todo o bloco abaixo** no chat do projeto **productivity-shine**.

---

## Prompt

````
Corrija a inconsistência de métricas de horas no painel. Hoje o KPI "Horas-máquina (horímetro)" usa horasMaquina (665,3 h), mas derivados.ts ainda usa horas_efetivas (727,2 h) para disponibilidade, L/h e tabela — isso gera L/h errado (9,57 em vez de 10,46) e tabela de disponibilidade com valores diferentes (ex.: trator 3305 mostra 8,2 h em vez de 6,7 h).

### REGRA ÚNICA (obrigatória em TODO o painel)

Criar/garantir helper central (se ainda não existir em lib/horas-maquina.ts ou utils):

```ts
export function parseNum(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

export function horasMaquina(row: {
  horas_horimetro?: number | string | null;
  horas_efetivas?: number | string | null;
  horas_operacao_calc?: number | string | null;
}): number {
  const horimetro = parseNum(row.horas_horimetro);
  if (horimetro > 0) return horimetro;
  return parseNum(row.horas_efetivas) || parseNum(row.horas_operacao_calc);
}
```

**Proibido** usar `row.horas_efetivas` diretamente em KPIs de horas operando, disponibilidade ou L/h.
**Permitido** usar horas_efetivas apenas em páginas de talhão/rendimento (ha/h), se fizer sentido operacional.

---

### 1. CORRIGIR src/lib/derivados.ts (ou arquivo equivalente)

Substituir TODAS as ocorrências de `.horas_efetivas` por `horasMaquina(row)` nos reduces.

**Antes (errado):**
```ts
.reduce((sum, r) => sum + parseNum(r.horas_efetivas), 0)
```

**Depois (correto):**
```ts
.reduce((sum, r) => sum + horasMaquina(r), 0)
```

Arquivo completo de referência:

```ts
import { useMemo } from "react";
import { useApontamentos, useOsParada, useAbastecimento } from "@/hooks/agro";
import { horasMaquina, parseNum } from "@/lib/horas-maquina";

function uniqueFrotas(ids: Array<string | null | undefined>): string[] {
  return [...new Set(ids.map((id) => String(id ?? "").trim()).filter(Boolean))];
}

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
        mes_key: null,
        id_frota,
        horas_operando,
        horas_parada,
        qtd_os: osFrota.length,
        disponibilidade_pct: total > 0 ? (horas_operando / total) * 100 : null,
      };
    });
  }, [apont, os]);
}

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
        mes_key: null,
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
```

---

### 2. CORRIGIR Visão Executiva (routes/index)

Garantir que **todos** estes pontos usem horasMaquina (já deve estar no KPI principal, conferir o restante):

| Componente | Deve usar |
|------------|-----------|
| KPI Horas-máquina | `apont.reduce((s,r) => s + horasMaquina(r), 0)` |
| KPI Disponibilidade | derivados → horas_operando via horasMaquina |
| KPI L/h | `G / K` onde K = soma horasMaquina das frotas com litros |
| Gráfico evolução diária | horasMaquina por dia (não horas_efetivas) |
| Top 12 tratores | horasMaquina |
| Tabela menor disponibilidade | derivados (horas_operando = horasMaquina) |

**Renomear labels:**
- Gráfico "Evolução diária": legenda `Horas efetivas` → **`Horas-máquina`**
- Subtitle: `Horas-máquina (horímetro) e área realizada por dia`

**Hint do KPI L/h:**
```tsx
hint={`${formatLitros(G)} L em tratores apontados · ${formatLitros(R)} L no período · base horímetro`}
```

---

### 3. CORRIGIR página Frota & Manutenção (se usar horas_efetivas)

Na tabela MTBF / confiabilidade e gráficos "Horas operando x paradas":
- Coluna **Horas operando** = horasMaquina (não horas_efetivas)
- MTBF = horasMaquina / falhas corretivas

---

### 4. BUSCA GLOBAL

Rodar busca no projeto por `horas_efetivas` e revisar cada uso:

| Contexto | Ação |
|----------|------|
| KPI / disponibilidade / L/h / ranking horas | Trocar por `horasMaquina(r)` |
| vw_prod_area_talhao (ha/h, rendimento) | Manter horas_efetivas se for regra de negócio de área |
| Operadores (turno vs operação) | Manter turno/op separados; horímetro já vem de horas_horimetro |

---

### 5. VALIDAÇÃO OBRIGATÓRIA (período 03/08–18/08, escopo TRATORES)

Após a correção, os números devem bater:

| KPI | Valor esperado |
|-----|----------------|
| Horas-máquina (horímetro) | **665,3 h** |
| Disponibilidade dos tratores | **~94,1%** (não 94,6%) |
| Consumo L/h | **~10,46 L/h** (6957 L ÷ 665,3 h) |
| Litros em tratores apontados | **6.957 L** |
| Litros totais tratores no período | **7.258 L** |
| Paradas manutenção | **74,7 h** (31 OS) |

**Tabela disponibilidade — conferir trator 3305:**
- Operando: **6,7 h** (não 8,2 h)
- Parada: 6,0 h
- Disponibilidade: **~52,8%**

**Tabela — trator 3369:**
- Operando: **140,0 h** (não 152,9 h)

Se L/h ainda mostrar 9,57, ainda existe horas_efetivas em algum derivado.

Não alterar filtro TRATORES, comboio_v2 nem exclusão da 920K — apenas unificar a métrica de horas.
````

---

## Arquivos de referência no repositório

| Arquivo | Descrição |
|---------|-----------|
| `dashboard-brand/reference/horas-maquina.ts` | Helper central |
| `dashboard-brand/reference/derivados.ts` | derivados.ts corrigido |
| `dashboard-brand/LOVABLE-PROMPT-HORIMETRO.md` | Este prompt |

---

## Diff mínimo (se preferir patch manual)

Em `derivados.ts`, apenas 2 linhas mudam de fato:

```diff
- .reduce((sum, r) => sum + parseNum(r.horas_efetivas), 0)
+ .reduce((sum, r) => sum + horasMaquina(r), 0)
```

São **duas ocorrências** (disponibilidade + combustível). Importar `horasMaquina` no topo do arquivo.
