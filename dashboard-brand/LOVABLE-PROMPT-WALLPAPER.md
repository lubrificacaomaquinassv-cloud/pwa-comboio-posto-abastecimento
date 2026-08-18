# Prompt Lovable — Fundo padrão Santa Virgínia

Cole no Lovable para aplicar o wallpaper oficial em **todas as páginas** do painel.

---

## Prompt

```
Aplique o fundo padrão Santa Virgínia em todo o painel (Visão Executiva, Operadores, Talhão, Frota, Custos).

ARQUIVOS (faça upload para public/assets/ ou src/assets/):
- dashboard-background-2560x1440.png  ← preferencial (QHD)
- dashboard-background.svg          ← fallback vetorial

PASSO 1 — Upload
Faça upload de dashboard-background-2560x1440.png nos assets do projeto.

PASSO 2 — Shell global
No layout raiz (App.tsx ou componente shell compartilhado por todas as rotas), envolva o conteúdo:

<div
  className="min-h-screen bg-background text-foreground bg-cover bg-fixed bg-center bg-no-repeat"
  style={{ backgroundImage: "url('/assets/dashboard-background-2560x1440.png')" }}
>
  {/* overlay escuro para legibilidade dos cards */}
  <div className="min-h-screen bg-background/72 backdrop-blur-[1px]">
    {/* header + main existentes */}
  </div>
</div>

PASSO 3 — Cards legíveis sobre o fundo
Garanta que cards KPI e tabelas usem:
- bg-card/75 ou bg-card/80
- border border-border/80
- backdrop-blur-sm nos cards principais

PASSO 4 — Header
Header sticky com backdrop-blur-md bg-background/85 border-b border-border/60.
Não colocar wallpaper no header — ele fica sobre o overlay.

PASSO 5 — Remover wallpaper antigo
Remover qualquer background-image JPG/URL externa anterior no shell.

CORES DE REFERÊNCIA (já no theme):
- Fundo base: oklch(17% 0.018 155) / #1a2420
- Verde primário: #5cb86a
- Azul institucional: #0d4f8b

Fontes: Sora (títulos) + Manrope (corpo).

Não alterar lógica de dados — apenas visual.
```

---

## Arquivos no repositório

```
dashboard-brand/assets/
├── dashboard-background.svg
├── dashboard-background-2560x1440.png   ← usar este
├── dashboard-background-1920x1080.png
└── dashboard-background-16x9.png
```

## Alternativa CSS (sem imagem)

Se preferir fundo gerado por CSS puro (sem upload):

```tsx
<div className="sv-dashboard-shell min-h-screen">
```

Importar `dashboard-brand/theme.css` — a classe `.sv-dashboard-shell` aplica gradiente + grid sutil equivalente ao PNG.
