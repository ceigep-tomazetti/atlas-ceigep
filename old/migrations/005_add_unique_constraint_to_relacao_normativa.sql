-- Migração 005: Adicionar constraint de unicidade para relacao_normativa
--
-- Garante que uma mesma relação (ex: ATO A -> ALTERA -> ATO B) não seja inserida
-- mais de uma vez na tabela. Isso é crucial para a idempotência do linker.

ALTER TABLE relacao_normativa
ADD CONSTRAINT relacao_normativa_unica_key
UNIQUE (ato_origem_id, ato_destino_id, tipo_relacao);
