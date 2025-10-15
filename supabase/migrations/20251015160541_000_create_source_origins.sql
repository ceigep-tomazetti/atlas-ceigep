-- Migração 000: Catálogo de Origens Legislativas
-- Cria a tabela fonte_origem para registrar canais oficiais de publicação

BEGIN;

CREATE TABLE public.fonte_origem (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(120) NOT NULL,
    esfera VARCHAR(40) NOT NULL,
    orgao_responsavel VARCHAR(160) NOT NULL,
    url_base TEXT NOT NULL,
    formato_padrao VARCHAR(40) NOT NULL,
    autenticacao_requerida BOOLEAN NOT NULL DEFAULT false,
    descricao TEXT,
    parametros_api JSONB,
    frequencia_atualizacao VARCHAR(40),
    status VARCHAR(32) NOT NULL DEFAULT 'em_validacao',
    observacoes TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX fonte_origem_nome_unq ON public.fonte_origem (nome);

COMMENT ON TABLE public.fonte_origem IS 'Catálogo de origens oficiais de atos normativos.';
COMMENT ON COLUMN public.fonte_origem.esfera IS 'federal, estadual, municipal…';
COMMENT ON COLUMN public.fonte_origem.parametros_api IS 'JSON com parâmetros padrão (ex.: ?status=publicado).';
COMMENT ON COLUMN public.fonte_origem.status IS 'Estados: em_validacao, ativo, obsoleto.';

COMMIT;
