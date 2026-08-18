# Referência — tabelas usadas pelo painel Lovable (estoque-verde-ouro.lovable.app)
# Projeto Supabase: azhpxhrwhegfysoeqmft
# As tabelas abaixo já existem no banco; este arquivo documenta a estrutura.

-- Catálogo de materiais (base do vw_catalogo_sap_campo / vw_painel_estoque_lista)
CREATE TABLE IF NOT EXISTS public.dim_catalogo_sap_campo (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo_sap        TEXT NOT NULL UNIQUE,
  descricao_sap     TEXT NOT NULL,
  descricao_resumida TEXT NOT NULL,
  unidade_estoque   TEXT NOT NULL DEFAULT 'UN',
  categoria         TEXT NOT NULL DEFAULT 'Defensivos',
  deposito_sap      TEXT NOT NULL DEFAULT 'FSV-MAN',
  ativo             BOOLEAN NOT NULL DEFAULT TRUE,
  fonte_arquivo     TEXT,
  observacao        TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Saldos exibidos no dashboard
CREATE TABLE IF NOT EXISTS public.estoque_sap_campo (
  codigo_sap      TEXT PRIMARY KEY,
  em_estoque      NUMERIC(14, 3) NOT NULL DEFAULT 0,
  unidade         TEXT NOT NULL DEFAULT 'UN',
  valor_unitario  NUMERIC(14, 4),
  atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Exemplo: incluir item 02333 manualmente (corrigido em 18/08/2026)
-- INSERT INTO public.dim_catalogo_sap_campo (codigo_sap, descricao_sap, descricao_resumida, unidade_estoque, categoria, deposito_sap, fonte_arquivo)
-- VALUES ('02333', 'GEL IRRIGAÇÃO FLOBOND A-30 SC 25 KG', 'Gel Irrigação Flobond A-30 SC 25 KG', 'KG', 'Defensivos', 'FSV-MAN', 'inclusao_manual');
--
-- INSERT INTO public.estoque_sap_campo (codigo_sap, em_estoque, unidade)
-- VALUES ('02333', 321, 'KG')
-- ON CONFLICT (codigo_sap) DO UPDATE SET em_estoque = EXCLUDED.em_estoque, unidade = EXCLUDED.unidade, atualizado_em = NOW();
