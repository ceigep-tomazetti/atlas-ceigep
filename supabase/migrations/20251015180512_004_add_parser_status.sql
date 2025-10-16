-- Migração 004: Status do parser e normalização

BEGIN;

ALTER TYPE public.status_fonte_documento ADD VALUE IF NOT EXISTS 'parsing' BEFORE 'processado';
ALTER TYPE public.status_fonte_documento ADD VALUE IF NOT EXISTS 'normalizado' AFTER 'processado';

ALTER TABLE public.fonte_documento
    ADD COLUMN IF NOT EXISTS status_parsing VARCHAR(32) DEFAULT 'pendente',
    ADD COLUMN IF NOT EXISTS parsing_executado_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS status_normalizacao VARCHAR(32) DEFAULT 'pendente',
    ADD COLUMN IF NOT EXISTS normalizacao_executado_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS caminho_parser_json TEXT,
    ADD COLUMN IF NOT EXISTS hash_parser_json VARCHAR(64);

COMMIT;
