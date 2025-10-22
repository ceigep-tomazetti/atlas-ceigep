-- Migração 006: Estrutura relacional para atos normativos e dispositivos LexML

BEGIN;

-- Tipos enumerados
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_dispositivo') THEN
        CREATE TYPE public.tipo_dispositivo AS ENUM (
            'titulo',
            'livro',
            'parte',
            'capitulo',
            'secao',
            'subsecao',
            'artigo',
            'paragrafo',
            'paragrafo_unico',
            'inciso',
            'alinea',
            'item',
            'dispositivo_auxiliar'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_relacao_normativa') THEN
        CREATE TYPE public.tipo_relacao_normativa AS ENUM (
            'altera',
            'revoga',
            'regulamenta',
            'consolida',
            'remete_a',
            'cita'
        );
    END IF;
END$$;

-- Tabela principal de atos normativos
CREATE TABLE public.ato_normativo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fonte_documento_id UUID NOT NULL UNIQUE REFERENCES public.fonte_documento(id) ON DELETE CASCADE,
    urn_lexml VARCHAR(255) NOT NULL UNIQUE,
    tipo_ato VARCHAR(80),
    titulo TEXT,
    ementa TEXT,
    orgao_publicador VARCHAR(160),
    data_legislacao DATE,
    data_publicacao DATE,
    status_vigencia VARCHAR(32),
    hash_texto_bruto VARCHAR(64),
    hash_json_estruturado VARCHAR(64),
    metadata_extra JSONB DEFAULT '{}'::jsonb,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ato_normativo_data_idx ON public.ato_normativo (data_legislacao DESC);
CREATE INDEX ato_normativo_status_idx ON public.ato_normativo (status_vigencia);

-- Tabela de dispositivos (artigos, incisos, etc.)
CREATE TABLE public.dispositivo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ato_id UUID NOT NULL REFERENCES public.ato_normativo(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES public.dispositivo(id) ON DELETE CASCADE,
    id_lexml VARCHAR(255) NOT NULL,
    tipo tipo_dispositivo NOT NULL,
    rotulo VARCHAR(160),
    texto TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    atributos JSONB DEFAULT '{}'::jsonb,
    hash_texto VARCHAR(64),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT dispositivo_id_lexml_unq UNIQUE (ato_id, id_lexml)
);

CREATE INDEX dispositivo_ato_idx ON public.dispositivo (ato_id, ordem);
CREATE INDEX dispositivo_parent_idx ON public.dispositivo (parent_id);
CREATE INDEX dispositivo_tipo_idx ON public.dispositivo (tipo);

-- Tabela de anexos (quadros, tabelas, etc.)
CREATE TABLE public.anexo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ato_id UUID NOT NULL REFERENCES public.ato_normativo(id) ON DELETE CASCADE,
    id_lexml VARCHAR(255),
    titulo TEXT,
    texto TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    hash_texto VARCHAR(64),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT anexo_id_lexml_unq UNIQUE (ato_id, id_lexml)
);

CREATE INDEX anexo_ato_idx ON public.anexo (ato_id, ordem);

-- Relações normativas entre dispositivos
CREATE TABLE public.dispositivo_relacao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ato_id UUID NOT NULL REFERENCES public.ato_normativo(id) ON DELETE CASCADE,
    dispositivo_origem_id UUID REFERENCES public.dispositivo(id) ON DELETE CASCADE,
    dispositivo_alvo_id UUID REFERENCES public.dispositivo(id) ON DELETE SET NULL,
    urn_alvo VARCHAR(255),
    tipo tipo_relacao_normativa NOT NULL,
    descricao TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT dispositivo_relacao_origem_chk CHECK (
        dispositivo_origem_id IS NOT NULL OR descricao IS NOT NULL
    )
);

CREATE INDEX dispositivo_relacao_ato_idx ON public.dispositivo_relacao (ato_id, tipo);
CREATE INDEX dispositivo_relacao_alvo_idx ON public.dispositivo_relacao (dispositivo_alvo_id);

-- Controle de versões textuais por dispositivo
CREATE TABLE public.versao_textual (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispositivo_id UUID NOT NULL REFERENCES public.dispositivo(id) ON DELETE CASCADE,
    hash_texto VARCHAR(64) NOT NULL,
    texto TEXT NOT NULL,
    vigencia_inicio DATE,
    vigencia_fim DATE,
    origem_alteracao VARCHAR(160),
    status_vigencia VARCHAR(32),
    anotacoes JSONB DEFAULT '{}'::jsonb,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT versao_textual_unq UNIQUE (dispositivo_id, hash_texto)
);

CREATE INDEX versao_textual_vigencia_idx ON public.versao_textual (dispositivo_id, vigencia_inicio, vigencia_fim);

COMMIT;
