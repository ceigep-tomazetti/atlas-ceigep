-- Migração 003: Adiciona a coluna status_vigencia à tabela versao_textual
--
-- O loader tenta inserir o status de vigência em cada versão, mas a coluna
-- não existia no schema inicial. Esta migração corrige essa inconsistência.

ALTER TABLE versao_textual
ADD COLUMN status_vigencia VARCHAR(50);
