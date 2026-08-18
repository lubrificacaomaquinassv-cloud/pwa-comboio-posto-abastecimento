# Prompt Lovable — Ajustes opcionais (não bloqueiam go-live)

Itens identificados na validação final. **Nenhum afeta a confiabilidade dos KPIs principais** — são melhorias de consistência metodológica ou manutenção de views.

---

## 1. View de abastecimento (backlog Supabase)

**Contexto:** `vw_prod_abastecimento_base` retorna **5.943 L** (52 registros) no período 03–18/08, enquanto `posto` + `comboio_v2` somam **7.258 L** (60 registros). O painel Frota usa corretamente as tabelas base para o total; a view está desatualizada/incompleta.

**Ação:** revisar a view no Supabase para incluir todos os registros de `posto` e `comboio_v2` (8 abastecimentos faltantes, ~1.315 L).

---

## 2. Hint de disponibilidade 94,1% (opcional UX)

**Contexto:** A disponibilidade exibida usa:

```
horímetro dos apontamentos ÷ (horímetro + paradas de frotas que operaram no período)
```

Paradas de frotas **sem horímetro no período** (3283, 3306, 3307, 3368) ficam de fora do denominador — daí 94,1% em vez de 89,9%.

**Prompt UX (opcional):**

```
Na aba Frota e Visão Executiva, adicionar hint abaixo do KPI Disponibilidade:

"Considera paradas apenas de tratores com horímetro apontado no período."

Ou renomear para "Disponibilidade (tratores em operação)".
```

---

## 3. MTBF — hint metodológico (opcional)

**Contexto:** MTBF 11,4 h = horas operando **somente das frotas que tiveram falha** ÷ 31 OS. MTTR 2,4 h e disponibilidade inerente 82,6% estão corretos e coerentes entre si.

**Prompt UX (opcional):**

```
Adicionar tooltip no KPI MTBF:
"Média de horas operando entre falhas, considerando apenas máquinas que registraram OS corretiva no período."
```

---

## 4. Operadores com apontamento incompleto (dado de campo)

MARCELO, ALEX e NILTON aparecem com 0 h turno mas horímetro > 0 — apontamentos incompletos no PWA, não bug do painel. Corrigir no lançamento de campo.
