-- Migração 003: Campos de extração de texto bruto

BEGIN;

ALTER TABLE public.fonte_documento
    ADD COLUMN IF NOT EXISTS caminho_texto_bruto TEXT,
    ADD COLUMN IF NOT EXISTS hash_texto_bruto VARCHAR(64),
    ADD COLUMN IF NOT EXISTS texto_extraido_em TIMESTAMPTZ;

COMMIT;
