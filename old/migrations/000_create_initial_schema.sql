-- Migração 000: Criação do Schema Inicial
--
-- Este script estabelece a estrutura fundamental de tabelas, tipos e extensões
-- para o banco de dados do projeto Atlas.

-- 1. Habilitar Extensões Essenciais
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Criar Tipos Customizados
CREATE TYPE status_processamento AS ENUM ('PENDENTE', 'COLETADO', 'PROCESSADO', 'FALHA');

-- 3. Criar Tabelas

CREATE TABLE ato_normativo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    urn_lexml VARCHAR(255) UNIQUE NOT NULL,
    tipo_ato VARCHAR(50) NOT NULL,
    titulo TEXT,
    ementa TEXT NOT NULL,
    entidade_federativa VARCHAR(50),
    orgao_publicador VARCHAR(255),
    data_publicacao DATE,
    fonte_oficial TEXT NOT NULL,
    hash_fonte VARCHAR(64),
    situacao_vigencia VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE dispositivo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ato_id UUID NOT NULL REFERENCES ato_normativo(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES dispositivo(id) ON DELETE CASCADE,
    rotulo VARCHAR(255) NOT NULL,
    ordem INTEGER,
    caminho_estrutural VARCHAR(255) NOT NULL,
    tipo_dispositivo VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(ato_id, caminho_estrutural)
);

CREATE TABLE versao_textual (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispositivo_id UUID REFERENCES dispositivo(id) ON DELETE CASCADE,
    texto_original TEXT,
    texto_normalizado TEXT NOT NULL,
    hash_texto_normalizado VARCHAR(64) NOT NULL,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE,
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    embedding vector(512), -- Dimensão inicial
    texto_normalizado_tsv tsvector
);

CREATE TABLE relacao_normativa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ato_origem_id UUID NOT NULL REFERENCES ato_normativo(id) ON DELETE CASCADE,
    ato_destino_id UUID NOT NULL REFERENCES ato_normativo(id) ON DELETE CASCADE,
    tipo_relacao VARCHAR(50) NOT NULL,
    propriedades JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE fonte_documento (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    urn_lexml VARCHAR(255) UNIQUE NOT NULL,
    url_fonte TEXT NOT NULL,
    status status_processamento NOT NULL DEFAULT 'PENDENTE',
    data_coleta TIMESTAMP WITH TIME ZONE,
    hash_conteudo_bruto VARCHAR(64),
    caminho_arquivo_local TEXT,
    metadados_fonte JSONB,
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Criar Índices
CREATE INDEX idx_ato_normativo_urn ON ato_normativo(urn_lexml);
CREATE INDEX idx_dispositivo_ato_id ON dispositivo(ato_id);
CREATE INDEX idx_versao_textual_dispositivo_id ON versao_textual(dispositivo_id);
CREATE INDEX idx_relacao_normativa_origem ON relacao_normativa(ato_origem_id);
CREATE INDEX idx_relacao_normativa_destino ON relacao_normativa(ato_destino_id);
CREATE INDEX idx_versao_textual_tsv ON versao_textual USING gin(texto_normalizado_tsv);
CREATE INDEX idx_versao_textual_embedding ON versao_textual USING hnsw (embedding vector_cosine_ops);
