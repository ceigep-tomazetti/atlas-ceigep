-- Migração 002: Estruturas de descoberta de fontes

BEGIN;

CREATE TYPE public.status_fonte_documento AS ENUM ('descoberto', 'processado', 'obsoleto');

CREATE TABLE public.fonte_documento (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fonte_origem_id UUID NOT NULL REFERENCES public.fonte_origem(id) ON DELETE CASCADE,
    urn_lexml VARCHAR(255) NOT NULL,
    tipo_ato VARCHAR(80),
    titulo TEXT,
    ementa TEXT,
    data_legislacao DATE,
    data_publicacao_diario DATE,
    orgao_publicador VARCHAR(160),
    url_fonte TEXT NOT NULL,
    metadados_brutos JSONB NOT NULL,
    status status_fonte_documento NOT NULL DEFAULT 'descoberto',
    hash_referencia VARCHAR(64),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (fonte_origem_id, urn_lexml)
);

CREATE INDEX fonte_documento_status_idx ON public.fonte_documento (status);
CREATE INDEX fonte_documento_fonte_idx ON public.fonte_documento (fonte_origem_id);

CREATE TABLE public.fonte_origem_execucao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fonte_origem_id UUID NOT NULL REFERENCES public.fonte_origem(id) ON DELETE CASCADE,
    periodo_inicio DATE,
    periodo_fim DATE,
    total_descobertos INTEGER NOT NULL DEFAULT 0,
    total_duplicados INTEGER NOT NULL DEFAULT 0,
    total_falhas INTEGER NOT NULL DEFAULT 0,
    observacoes TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'concluido',
    iniciado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finalizado_em TIMESTAMPTZ
);

CREATE INDEX fonte_origem_execucao_fonte_idx ON public.fonte_origem_execucao (fonte_origem_id);

COMMIT;
