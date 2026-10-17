# Prompt para colar no Lovable

Copie o bloco abaixo integralmente no chat do projeto **productivity-shine**.

---

## Prompt

```
Atualize o Painel de Produtividade Operacional com as regras oficiais abaixo.

### PADRÃO VISUAL
1. Importe o wallpaper oficial: dashboard-background-2560x1440.png (pasta dashboard-brand/assets).
2. Aplique como fundo fixo no shell principal (bg-cover bg-center bg-fixed) com overlay escuro leve para legibilidade.
3. Mantenha fontes Sora (títulos) e Manrope (corpo).
4. Use as CSS variables do theme.css fornecido (verde oklch 72% 0.16 145, fundo oklch 17% 0.018 155).

### FILTRO DE FROTA — SOMENTE TRATORES
Substituir o escopo "AGRICOLA" por "TRATORES":
- Renomear botão "Agrícola" para "Tratores".
- Default do painel: escopo TRATORES (horas-máquina).
- Remover caminhões, motos, veículos leves, implementos e terceiros.

Implementar frotasTratores assim:
```ts
const CATEGORIAS_EXCLUIDAS = new Set(["CAMINHAO","MOTO","VEICULO LEVE","TERCEIRO","IMPLEMENTO"]);
const FROTAS_TERCEIRAS = new Set(["920K","920 K"]);
const norm = (v) => String(v ?? "").trim().toUpperCase();
const isTrator = (row) => norm(row.modelo).includes("TRATOR");

function buildFrotasTratores(dimFrota) {
  const set = new Set();
  for (const row of dimFrota ?? []) {
    const id = norm(row.id_frota);
    if (!id || FROTAS_TERCEIRAS.has(id)) continue;
    if (CATEGORIAS_EXCLUIDAS.has(norm(row.categoria))) continue;
    if (isTrator(row)) set.add(id);
  }
  return set;
}
```

No filtro Ys(), quando escopo === "TRATORES", excluir qualquer registro cujo id_frota não esteja em frotasTratores.

Lista fixa de tratores (18): 3014, 3019, 3281, 3283, 3305, 3306, 3307, 3336, 3337, 3350, 3363, 3368, 3369, 3380, 3393, 3394, 3396, 3402.

IMPORTANTE: 920K é equipamento de TERCEIROS — nunca incluir.

Excluir também EQUIPAMENTO que não é trator: 3272, 3285, 3320, 3345, 3354 (carregadeiras, patrol, harvester).

### DADOS / SUPABASE
- Abastecimento comboio: tabela oficial comboio_v2 (via vw_prod_abastecimento_base, origem comboio_v2).
- Não usar tabela comboio legada.

### HORAS-MÁQUINA
Priorizar horas_trabalhadas (horímetro) como métrica principal de horas efetivas quando disponível.
Manter horas_operacao_calc apenas como fallback.

### UI
- Header: logo Santa Virgínia + "Painel de Análise de Produtividade Operacional".
- Remover opção "Toda a frota" por enquanto OU deixá-la desabilitada; foco total em Tratores.
- Atualizar hints dos KPIs para refletir "tratores" em vez de "máquinas agrícolas".
```

---

## Após aplicar

Validar no período 03/08–18/08/2026:

- 920K não aparece em nenhum gráfico ou tabela
- Caminhões (categoria CAMINHAO) ausentes
- Carregadeira 3285 e patrol ausentes
- Apenas ~18 tratores nos rankings
- Consumo diesel coerente só com tratores apontados
