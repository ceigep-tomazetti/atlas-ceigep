-- Migração 001: Configuração do Full-Text Search para Português
--
-- Cria uma nova configuração de busca de texto completo para o português,
-- baseada no dicionário 'portuguese', mas com o adicional de remover acentos.
-- Isso permite que buscas como "constituicao" encontrem "constituição".

-- 1. Cria a extensão unaccent se ela não existir
CREATE EXTENSION IF NOT EXISTS unaccent;

-- 2. Cria a configuração de busca de texto 'portuguese_unaccent'
CREATE TEXT SEARCH CONFIGURATION public.portuguese_unaccent (
    COPY = pg_catalog.portuguese
);

-- 3. Altera a configuração para usar o dicionário 'unaccent'
-- Isso fará com que os acentos sejam removidos antes da busca.
ALTER TEXT SEARCH CONFIGURATION public.portuguese_unaccent
    ALTER MAPPING FOR hword, hword_part, word
    WITH unaccent, portuguese_stem;
