# 🚢 Diário de Bordo – Projeto Atlas (Parte 2)

Este documento continua o registro de tarefas após a ocorrência de erros de API no arquivo original.

---

### Data: 2025-10-13

**Tarefa:** 3.4 - Implementar normalizador

**Detalhes:**

1.  **Criação do Normalizador:** Foi criado o diretório `normalizer/` e o script `normalizer.py`, que aceita como entrada um arquivo JSON gerado pelo parser.
2.  **Implementação da Regra #1:** O script foi implementado para percorrer a árvore de dispositivos e remover referências legislativas entre parênteses (ex: `(Vide Lei...)`, `(Redação dada por...)`).
3.  **Auditoria:** A lógica para preservar o texto original (`texto_original_parser`), adicionar um bloco de auditoria (`normalizacao`) e gerar um novo hash para o texto limpo (`hash_texto_normalizado`) foi implementada.
4.  **Execução e Geração:** O normalizador foi executado com sucesso para os três atos normativos do escopo (CF, CE-GO, LO-AP), gerando os respectivos arquivos `_normalizado.json`, `_diff.md` e logs.

**Conclusão da Tarefa:** A tarefa 3.4 está concluída. Temos um normalizador funcional com a primeira regra de limpeza implementada e validada para todo o nosso corpus.

---

### Data: 2025-10-13

**Tarefa:** 3.5 - Criar pipeline de carga (ETL)

**Detalhes:**

1.  **Ambiente do Loader:** Foi criado o diretório `loader/` e o script `loader.py`, com as dependências para PostgreSQL e Neo4j.
2.  **Correção de Schema (Postgres):** O schema do PostgreSQL foi corrigido para adicionar as colunas `parent_id` (em `dispositivo`) e `texto_original` (em `versao_textual`), e para renomear `hash_texto` para `hash_texto_normalizado`, alinhando o banco com os dados gerados.
3.  **Desenvolvimento do Loader:** O script `loader.py` foi implementado para ler um arquivo JSON normalizado e carregar os dados de forma hierárquica em ambos os bancos de dados.
4.  **Execução e Validação:** O loader foi executado com sucesso para a Lei Orgânica de Aparecida. A validação confirmou que os dados foram inseridos corretamente no PostgreSQL (incluindo a relação `parent_id`) e no Neo4j (com a criação de nós e relacionamentos `[:CONTEM]`).

**Conclusão da Tarefa:** A tarefa 3.5 está concluída. Temos um pipeline de ETL funcional que popula nossos bancos de dados a partir dos arquivos JSON processados.

---

### Data: 2025-10-13

**Tarefa:** 3.6 - Criar rotina de verificação de integridade

**Detalhes:**

1.  **Criação do Verificador:** Foi criado o diretório `integrity_checker/` com o script `checker.py`. O objetivo do script é comparar os dados dos arquivos `_normalizado.json` (a "verdade") com o que foi carregado no PostgreSQL e no Neo4j.

2.  **Processo de Depuração Intenso:**
    *   Uma `SyntaxError` inicial no script, causada por uma f-string mal formatada, levou a múltiplas tentativas de correção. O problema se mostrou complexo de depurar, exigindo a criação de scripts de teste isolados.
    *   Após a correção da sintaxe, o script executou, mas falhou em se conectar ao Neo4j devido a credenciais incorretas. O arquivo `.env` foi corrigido para usar a senha `atlas_password`, alinhando-o com o `docker-compose.yml`.
    *   Com a conexão bem-sucedida, o script passou a falhar na consulta de hashes no PostgreSQL e reportar um aviso no Neo4j. A análise dos schemas e do `loader.py` revelou que os nomes das propriedades dos hashes estavam incorretos nas consultas do checker. As queries foram corrigidas para usar `hash_texto_normalizado` no PG e `hash` no Neo4j.
    *   Finalmente, a extração dos dados do JSON ("ground truth") estava falhando, retornando 0 dispositivos. Uma análise detalhada da estrutura do JSON de saída do normalizador revelou que a chave correta era `dispositivos` (plural) no nível raiz, e não `dispositivo` aninhado em `ato_normativo`.

3.  **Execução e Descoberta Crítica:**
    *   Após todas as correções, o `checker.py` foi executado para os três atos normativos.
    *   **Resultado:** O script executou com sucesso, mas reportou **FALHA** na integridade dos dados para todos os atos carregados após o primeiro.
    *   **Diagnóstico:** A leitura dos relatórios gerados (`*_integrity_report.md`) mostrou que os dados no PostgreSQL estavam **corretos e íntegros**. No entanto, o banco de dados Neo4j estava **corrompido**.
    *   **Causa Raiz:** O `loader.py` não isola os dispositivos por ato no Neo4j. Ele cria nós de `Dispositivo` usando um `caminho_estrutural` (ex: `art-1`) que não é globalmente único. Ao carregar múltiplos atos, ele cria relações `[:CONTEM]` ambíguas, conectando dispositivos de um ato ao grafo de outro. O checker encontrou `170` dispositivos no grafo da Lei Orgânica, que na verdade é o total de dispositivos de todos os atos carregados.

**Conclusão da Tarefa:** A tarefa 3.6 está **concluída**. O script `integrity_checker/checker.py` foi finalizado e se provou uma ferramenta de QA **essencial**, ao identificar um bug crítico de corrupção de dados no `loader.py` (tarefa 3.5) que não havia sido pego anteriormente. Os relatórios gerados documentam a falha com precisão. A correção do loader será a próxima prioridade.

---

### Data: 2025-10-13

**Tarefa:** Correção do Bug do Loader e Teste de Pipeline Completo

**Detalhes:**

1.  **Correção do `loader.py`:**
    *   A função `insert_neo4j` foi reescrita para usar um identificador globalmente único (`id_unico`) para cada nó `Dispositivo`, formado pela `urn_lexml` do ato e pelo `caminho_estrutural` do dispositivo.
    *   Todas as cláusulas `MATCH` no `loader` foram atualizadas para usar este novo `id_unico`, garantindo que os relacionamentos `[:CONTEM]` sejam criados apenas dentro do escopo do ato normativo correto.
    *   A função `insert_postgres` também foi validada para garantir que lia a estrutura de dados JSON corretamente.

2.  **Limpeza dos Bancos de Dados:**
    *   Os bancos de dados, que estavam em um estado corrompido, foram completamente limpos para garantir um teste válido.
    *   **PostgreSQL:** O comando `TRUNCATE TABLE ... CASCADE` foi executado.
    *   **Neo4j:** O comando `MATCH (n) DETACH DELETE n` foi executado.

3.  **Teste de Pipeline End-to-End:**
    *   O `loader.py` corrigido foi executado sequencialmente para os três atos normativos (LO-AP, CE-GO, CF).
    *   O `integrity_checker.py` foi executado para cada um dos três atos após o carregamento.

4.  **Validação Final:**
    *   **Resultado:** Todos os três testes de integridade passaram com **sucesso**.
    *   A correção foi **validada**, e o pipeline de dados (Parser → Normalizer → Loader → Checker) agora está robusto e livre de corrupção de dados entre os atos.

**Conclusão:** O bug crítico do loader foi corrigido e todo o pipeline de ingestão foi validado com sucesso. O projeto está novamente em um estado estável e pronto para as próximas etapas.

---

### Data: 2025-10-13

**Tarefa:** Teste de Estresse do Pipeline com Novas Leis e Correção do Parser HTML

**Detalhes:**

1.  **Objetivo:** Validar a robustez do pipeline com novas leis e, ao mesmo tempo, implementar a funcionalidade de parsing de HTML que estava ausente.

2.  **Processo de Refatoração do Parser:**
    *   O `parser/main.py` foi profundamente refatorado para remover a dependência de metadados "hardcoded" (`METADATA_OVERRIDES`).
    *   Foi introduzida uma interface de linha de comando (CLI) que opera com arquivos de **manifesto** (`.json`), tornando o parser configurável e desacoplado.
    *   A lógica de parsing de PDF foi corrigida e validada com uma nova lei municipal, que foi processada com sucesso de ponta a ponta.
    *   A função `parse_html` foi implementada com `BeautifulSoup` para extrair artigos de documentos HTML de forma genérica.

3.  **Correção de Bug no Loader (PostgreSQL):**
    *   Durante a ingestão da LAI (HTML), um erro de `value too long` ocorreu no PostgreSQL.
    *   O `loader.py` foi depurado, identificando que a coluna `rotulo` na tabela `dispositivo` era `VARCHAR(255)`, insuficiente para alguns textos de artigos.
    *   O schema do PostgreSQL foi alterado (`ALTER TABLE`), mudando a coluna `rotulo` para o tipo `TEXT`.

4.  **Validação Final do Pipeline HTML:**
    *   Após a correção do schema e a limpeza dos bancos de dados, o pipeline completo foi re-executado para a LAI.
    *   **Resultado:** A Lei de Acesso à Informação (HTML) foi processada com **sucesso**, com o `integrity_checker` confirmando a integridade dos dados.

**Conclusão:** O teste de estresse foi concluído com sucesso. O pipeline agora é capaz de processar tanto PDFs quanto HTMLs de fontes externas. A refatoração do parser e a correção do schema do banco de dados tornaram o sistema significativamente mais robusto e flexível. O projeto está pronto para avançar para a próxima tarefa do plano original.

---

### Data: 2025-10-13

**Tarefa:** Teste de Integração Final do Pipeline Completo

**Detalhes:**

1.  **Objetivo:** Realizar um teste de ponta a ponta com todo o corpus legislativo coletado até o momento para garantir a estabilidade e robustez do pipeline após as múltiplas refatorações e correções de bugs.

2.  **Preparação do Ambiente:**
    *   **Limpeza de Artefatos:** Todos os arquivos gerados anteriormente nos diretórios `parser/output`, `normalizer/output` e `integrity_checker/output` foram removidos.
    *   **Limpeza dos Bancos de Dados:** Os bancos de dados PostgreSQL e Neo4j foram completamente zerados para garantir que não houvesse dados residuais de execuções anteriores.

3.  **Execução do Pipeline:**
    *   O pipeline completo (Parser → Normalizer → Loader → Checker) foi executado em sequência para os seguintes 5 atos normativos, processando os textos na íntegra:
        1.  Constituição Federal (HTML)
        2.  Constituição de Goiás (HTML)
        3.  Lei Orgânica de Aparecida de Goiânia (PDF)
        4.  Lei de Acesso à Informação (HTML)
        5.  Lei Municipal Nº 2.229/2001 de Aparecida de Goiânia (PDF)

4.  **Resultado:**
    *   **SUCESSO:** Todos os cinco atos foram processados com sucesso, e o `integrity_checker` validou a integridade dos dados para cada um deles, confirmando que a carga no PostgreSQL e no Neo4j foi correta e sem corrupção de dados.

**Conclusão:** O teste de integração final foi um sucesso. O pipeline de ingestão está estável e validado para o corpus atual. O Bloco 3 do plano de tarefas está significativamente avançado. O projeto está pronto para prosseguir para a próxima etapa: **3.7 - Gerar embeddings por dispositivo**.