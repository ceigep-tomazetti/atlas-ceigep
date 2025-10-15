-- Migração 002: Altera a dimensão dos vetores de embedding
--
-- O novo modelo de embedding (stjiris/bert-large-portuguese-cased-legal-mlm-gpl-nli-sts-v1)
-- produz vetores de 1024 dimensões, enquanto o modelo anterior produzia 512.
-- Esta migração atualiza a coluna para acomodar os novos vetores.

ALTER TABLE versao_textual
ALTER COLUMN embedding TYPE vector(1024);

-- ATENÇÃO: Após executar esta migração, todos os embeddings existentes
-- devem ser recalculados e atualizados.
