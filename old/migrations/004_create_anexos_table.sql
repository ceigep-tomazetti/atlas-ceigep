-- Migração 004: Criação da tabela de anexos
--
-- Adiciona uma tabela para armazenar o conteúdo de anexos (Quadros, etc.)
-- que são referenciados no corpo do ato normativo.

CREATE TABLE anexo_ato_normativo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ato_id UUID NOT NULL REFERENCES ato_normativo(id) ON DELETE CASCADE,
    titulo VARCHAR(255),
    texto_bruto TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_anexo_ato_id ON anexo_ato_normativo(ato_id);
