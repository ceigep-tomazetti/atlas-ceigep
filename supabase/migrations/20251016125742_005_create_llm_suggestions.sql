BEGIN;

CREATE TYPE public.llm_sugestao_status AS ENUM ('pendente', 'implementada', 'ignorada');

CREATE TABLE public.llm_parser_sugestao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fonte_documento_id UUID REFERENCES public.fonte_documento(id) ON DELETE SET NULL,
    fonte_origem_id UUID REFERENCES public.fonte_origem(id) ON DELETE SET NULL,
    urn_lexml VARCHAR(255) NOT NULL,
    heuristicas TEXT,
    json_deterministico JSONB,
    json_llm JSONB,
    sugestao TEXT NOT NULL,
    status llm_sugestao_status NOT NULL DEFAULT 'pendente',
    observacoes TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX llm_parser_sugestao_urn_idx ON public.llm_parser_sugestao (urn_lexml);
CREATE INDEX llm_parser_sugestao_status_idx ON public.llm_parser_sugestao (status);

COMMIT;
