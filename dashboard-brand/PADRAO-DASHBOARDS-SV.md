# Padrão Visual — Dashboards Santa Virgínia

Kit oficial para reutilizar no Lovable e em novos painéis operacionais.

## Identidade

| Elemento | Valor |
|----------|-------|
| Marca | Santa Virgínia Agropecuária e Florestal |
| Tipografia títulos | **Sora** 600/700 |
| Tipografia corpo | **Manrope** 400–700 |
| Verde primário | `oklch(72% 0.16 145)` · `#5cb86a` |
| Azul institucional | `#0d4f8b` |
| Fundo base | `oklch(17% 0.018 155)` · `#1a2420` |
| Cards | `oklch(22% 0.02 155)` com borda `white/12%` |

## Arquivos deste kit

```
dashboard-brand/
├── assets/
│   ├── dashboard-background.svg           # vetorial (escala infinita)
│   ├── dashboard-background-1920x1080.png   # Full HD
│   ├── dashboard-background-2560x1440.png # QHD (recomendado)
│   └── dashboard-background-16x9.png      # alternativa gerada
├── theme.css                              # variáveis CSS + classe .sv-dashboard-shell
├── reference/
│   └── fleet-filter.ts                    # filtro oficial TRATORES
├── LOVABLE-PROMPT-TRATORES.md             # prompt pronto para colar no Lovable
└── PADRAO-DASHBOARDS-SV.md                # este arquivo
```

## Como aplicar no Lovable

### 1. Upload do wallpaper

1. Abra o projeto no Lovable.
2. Faça upload de `assets/dashboard-background-2560x1440.png` (ou o SVG).
3. Aplique no container raiz (`min-h-screen`):

```tsx
<div className="sv-dashboard-shell min-h-screen">
  {/* conteúdo */}
</div>
```

Ou inline:

```tsx
<div
  className="min-h-screen bg-background bg-cover bg-fixed bg-center"
  style={{ backgroundImage: "url('/assets/dashboard-background-2560x1440.png')" }}
>
```

### 2. Importar tema

Copie `theme.css` para `src/styles/theme-sv.css` e importe no entrypoint:

```tsx
import "./styles/theme-sv.css";
```

### 3. Header padrão

- Logo Santa Virgínia (canto esquerdo, 44×44 px, `rounded-lg`)
- Título: **Santa Virgínia**
- Subtítulo: **Painel de Análise de Produtividade Operacional**
- Header sticky, `backdrop-blur`, `bg-background/85`, borda inferior

### 4. Cards KPI

- Grid responsivo 2→4→6 colunas
- Valor grande + unidade + hint secundário
- Cards com `bg-card/70`, `border-border`, `rounded-lg`

---

## Regras de dados (oficial)

### Abastecimento

| Tabela | Status |
|--------|--------|
| `comboio_v2` | ✅ Fonte oficial comboio |
| `posto` | ✅ Fonte oficial posto |
| `comboio` (legado) | ❌ Não usar |

View: `vw_prod_abastecimento_base` (`origem`: `posto` | `comboio_v2`)

### Escopo de frota — TRATORES (horas-máquina)

**Incluir:** frotas em `dim_frota` cujo `modelo` contém `TRATOR` (18 tratores).

**Excluir sempre:**

- `CAMINHAO`, `MOTO`, `VEICULO LEVE`, `TERCEIRO`, `IMPLEMENTO`
- Terceiros: `920K`, `920 K` (não é equipamento da fazenda)
- Placas de veículos leves (regex Mercosul)
- EQUIPAMENTO que não é trator: carregadeiras (3272, 3345, 3354), patrol (3285), harvester (3320)

**Substituir no painel:**

- Label do filtro: `Agrícola` → **`Tratores`**
- Valor interno: `escopo: "TRATORES"` (antes `"AGRICOLA"`)
- Default: **`TRATORES`** (sem toggle caminhões neste momento)

### Métrica principal de horas

Para painéis de **horas-máquina**, priorizar:

1. `horas_trabalhadas` (delta horímetro) quando disponível
2. Fallback: `horas_operacao_calc` apenas se horímetro ausente

---

## Paleta de gráficos (ECharts)

```js
const SV_CHART_COLORS = [
  "oklch(78% 0.16 140)", // chart-1 verde
  "oklch(82% 0.15 130)", // chart-2
  "oklch(82% 0.16 85)",  // chart-3 amarelo-verde
  "oklch(72% 0.12 230)", // chart-4 azul
  "oklch(68% 0.17 30)",  // chart-5 laranja
];
```

---

## Checklist antes de publicar

- [ ] Wallpaper padrão aplicado
- [ ] Fontes Sora + Manrope carregadas
- [ ] Filtro **Tratores** ativo por padrão
- [ ] 920K / terceiros excluídos
- [ ] Caminhões e veículos leves excluídos
- [ ] Comboio lendo `comboio_v2` (via view)
- [ ] Logo Santa Virgínia no header
