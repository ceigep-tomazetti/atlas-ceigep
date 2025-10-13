-- =============================================================================
-- 📜 SCHEMA POSTGRES – PROJETO ATLAS
--
-- Versão: 1.0
-- Data: 2025-10-12
--
-- Este script define a estrutura de tabelas para o banco de dados PostgreSQL,
-- que serve como a base transacional e de busca vetorial do Atlas.
-- =============================================================================

-- Habilita a extensão para gerar UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Habilita a extensão pgvector para busca semântica
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabela principal para os atos normativos
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

-- Tabela para os dispositivos textuais (artigos, parágrafos, etc.)
CREATE TABLE dispositivo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ato_id UUID NOT NULL REFERENCES ato_normativo(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES dispositivo(id) ON DELETE CASCADE, -- Auto-referência para hierarquia
    rotulo VARCHAR(255) NOT NULL,
    ordem INTEGER,
    caminho_estrutural VARCHAR(255) NOT NULL,
    tipo_dispositivo VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(ato_id, caminho_estrutural) -- Garante que o caminho é único por ato
);

-- Tabela para as versões temporais do texto de um dispositivo
-- É aqui que o conteúdo textual e os embeddings são armazenados
CREATE TABLE versao_textual (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispositivo_id UUID REFERENCES dispositivo(id) ON DELETE CASCADE,
    texto_original TEXT,
    texto_normalizado TEXT NOT NULL,
    hash_texto_normalizado VARCHAR(64) NOT NULL,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE,
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- A dimensão (512) deve corresponder à saída do modelo de embedding
    embedding vector(512),
    -- Coluna para Full-Text Search (BM25)
    texto_normalizado_tsv tsvector
);

-- Índice para busca vetorial (similaridade de cosseno)
CREATE INDEX idx_versao_textual_embedding ON versao_textual USING hnsw (embedding vector_cosine_ops);

-- Índice para busca textual (BM25)
CREATE INDEX idx_versao_textual_tsv ON versao_textual USING gin(texto_normalizado_tsv);

-- Tabela para armazenar as relações entre atos normativos (ex: revoga, altera)
CREATE TABLE relacao_normativa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ato_origem_id UUID NOT NULL REFERENCES ato_normativo(id) ON DELETE CASCADE,
    ato_destino_id UUID NOT NULL REFERENCES ato_normativo(id) ON DELETE CASCADE,
    tipo_relacao VARCHAR(50) NOT NULL, -- ALTERA, REVOGA, REGULAMENTA, etc.
    propriedades JSONB, -- Para armazenar metadados como 'escopo', 'pinpoint'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices para otimização de consultas
CREATE INDEX idx_ato_normativo_urn ON ato_normativo(urn_lexml);
CREATE INDEX idx_dispositivo_ato_id ON dispositivo(ato_id);
CREATE INDEX idx_versao_textual_dispositivo_id ON versao_textual(dispositivo_id);
CREATE INDEX idx_relacao_normativa_origem ON relacao_normativa(ato_origem_id);
CREATE INDEX idx_relacao_normativa_destino ON relacao_normativa(ato_destino_id);

-- Índice HNSW para busca vetorial eficiente (pgvector)
CREATE INDEX idx_versao_textual_embedding ON versao_textual USING hnsw (embedding vector_l2_ops);
