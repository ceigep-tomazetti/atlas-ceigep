// =============================================================================
// 📜 SCHEMA NEO4J – PROJETO ATLAS
//
// Versão: 1.4 (Community-safe)
// Data: 2025-10-12
//
// Este script define o esquema para o banco de dados Neo4j, contendo apenas
// as features suportadas pela Community Edition. A validação de existência
// de campos é delegada para a camada de aplicação (ETL).
// =============================================================================


// =============================================================================
// 1. MODELO DE DADOS (DOCUMENTAÇÃO)
// =============================================================================

// --- Nós (Labels) ---
//
// :AtoNormativo
//   - Propriedades Obrigatórias (validadas no ETL): urn_lexml, tipo_ato, ementa, fonte_oficial, situacao_vigencia.
//
// :Dispositivo
//   - Propriedades Obrigatórias (validadas no ETL): chave_unica_dispositivo, rotulo, caminho_estrutural, tipo_dispositivo.
//
// :VersaoTextual
//   - Propriedades Obrigatórias (validadas no ETL): vigencia_inicio, texto_normalizado, hash_texto, status_vigencia.


// =============================================================================
// 2. CONSTRAINTS E ÍNDICES (COMMUNITY-SAFE)
// =============================================================================

// --- Constraints de Unicidade ---

// Garante que cada AtoNormativo tenha uma URN única.
CREATE CONSTRAINT ato_urn IF NOT EXISTS
FOR (n:AtoNormativo) REQUIRE n.urn_lexml IS UNIQUE;

// Garante que um Dispositivo seja único através de uma chave derivada.
CREATE CONSTRAINT dispositivo_chave_unica IF NOT EXISTS
FOR (d:Dispositivo) REQUIRE d.chave_unica_dispositivo IS UNIQUE;

// --- Índices Úteis ---

// Otimiza a busca por tipo de ato.
CREATE INDEX ato_tipo_ato IF NOT EXISTS
FOR (n:AtoNormativo) ON (n.tipo_ato);

// Otimiza a busca por caminho estrutural (útil para navegação).
CREATE INDEX dispositivo_caminho_estrutural IF NOT EXISTS
FOR (n:Dispositivo) ON (n.caminho_estrutural);


// =============================================================================
// 3. REGRAS DE ETL (LÓGICA NA APLICAÇÃO)
// =============================================================================

/*
Antes de inserir dados no Neo4j, o processo de ETL DEVE:

1. Validar a presença e o formato dos campos obrigatórios para cada entidade.

2. Montar a chave derivada para unicidade do Dispositivo:
   - `chave_unica_dispositivo` = `{urn_do_ato}|{caminho_do_dispositivo}`

3. Usar `MERGE` com base na chave única de cada nó para evitar duplicatas:
   - `MERGE (a:AtoNormativo { urn_lexml: $urn })`
   - `MERGE (d:Dispositivo { chave_unica_dispositivo: $chave_unica })`

4. Rejeitar ou registrar como erro qualquer registro que não passe nas validações.
*/


// =============================================================================
// 4. CONSULTAS DE SANIDADE E AUDITORIA
// =============================================================================

/*
// Dispositivos duplicados por ato (deve retornar 0 linhas)
MATCH (a:AtoNormativo)-[:CONTEM]->(d:Dispositivo)
WITH a.urn_lexml AS ato, d.caminho_estrutural AS caminho, count(*) AS c
WHERE c > 1
RETURN ato, caminho, c;

// Dispositivos sem versão textual
MATCH (d:Dispositivo)
WHERE NOT (d)-[:POSSUI_VERSAO]->(:VersaoTextual)
RETURN d.chave_unica_dispositivo LIMIT 50;

// Relações ALTERA/REVOGA sem a propriedade `pinpoint`
MATCH ()-[r:ALTERA|REVOGA]->()
WHERE r.pinpoint IS NULL
RETURN r LIMIT 50;
*/


// =============================================================================
// 5. PLANO DE MIGRAÇÃO (PARA NEO4J ENTERPRISE)
// =============================================================================

/*
Se o projeto migrar para a versão Enterprise, as seguintes melhorias podem ser feitas:

1.  **Trocar Imagem Docker:** Mudar para `neo4j:5.x-enterprise` e aceitar a licença.
2.  **Reintroduzir Constraints:**
    - `CREATE CONSTRAINT ... REQUIRE (n.prop) IS NOT NULL` para todos os campos obrigatórios.
    - Substituir a `chave_unica_dispositivo` por uma `NODE KEY` composta: `REQUIRE (n.ato_urn, n.caminho_estrutural) IS NODE KEY`.
3.  **Ajustar ETL:** As validações de existência de campo no ETL podem ser removidas (ou mantidas por segurança).
*/
