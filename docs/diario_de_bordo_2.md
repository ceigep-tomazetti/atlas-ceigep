# 🚢 Diário de Bordo – Projeto Atlas (Parte 2)

Este documento continua o registro de tarefas após a ocorrência de erros de API no arquivo original.

---

### Data: 2025-10-13

**Tarefa:** 3.9 - Testar pipeline completo com novas fontes

**Detalhes:**

1.  **Objetivo:** Validar a robustez do pipeline de ingestão de ponta a ponta com múltiplas fontes de dados reais e desconhecidas.
2.  **Coleta de Fontes:** Foram fornecidos 4 links de API para PDFs de leis ordinárias do Estado de Goiás.
3.  **Processo de Depuração:** A primeira tentativa de ingestão falhou silenciosamente. A depuração revelou que o `web_fetch` estava salvando o texto extraído de um PDF como um arquivo de texto, em vez de salvar o conteúdo binário do PDF. Isso causava uma falha irrecuperável na biblioteca `PyMuPDF` do parser.
4.  **Correção:** O processo foi corrigido para usar `curl` para baixar e salvar o conteúdo binário dos PDFs corretamente.
5.  **Execução do Pipeline:** O pipeline completo (Parser → Normalizer → Loader → Checker) foi executado com sucesso para as 4 novas leis ordinárias.
6.  **Pós-processamento:** Após a ingestão, os scripts `embedder` e `linker` foram executados para gerar os embeddings dos novos dispositivos e para buscar novas relações, respectivamente.

**Conclusão da Tarefa:** A tarefa 3.9 foi concluída com sucesso. O pipeline provou ser robusto o suficiente para ingerir novas fontes de dados (PDFs via API) sem a necessidade de alterações no código, e o processo de depuração levou a uma melhor compreensão do tratamento de arquivos binários.

---

### Data: 2025-10-13

**Tarefa:** 4.1, 4.2, 4.3 - Validação do Esquema e Relações Base do Grafo

**Detalhes:**

1.  **Aplicação do Schema (4.1):** Os comandos `CREATE CONSTRAINT` e `CREATE INDEX` do arquivo `schema_neo4j.cypher` foram executados com sucesso, garantindo a unicidade de URNs e dispositivos, e otimizando as buscas.
2.  **Validação de `[:CONTEM]` (4.2):** Uma consulta de contagem no Neo4j confirmou a existência de **2604** relações `[:CONTEM]`, validando que o `loader` está construindo corretamente a hierarquia dos atos.
3.  **Validação de `[:POSSUI_VERSAO]` (4.3):** Uma consulta similar confirmou **2604** relações `[:POSSUI_VERSAO]`, validando que cada dispositivo está conectado à sua versão textual.

**Conclusão da Tarefa:** As tarefas base de estruturação do grafo foram formalmente concluídas e validadas.

---

### Data: 2025-10-13

**Tarefa:** 4.4 & 4.5 - Detectar Relações Normativas (ALTERA, REVOGA, REGULAMENTA, REMETE_A)

**Detalhes:**

1.  **Evolução do `linker`:** O script `linker/main.py` foi progressivamente aprimorado para detectar múltiplos tipos de relações textuais.
2.  **Detecção de `ALTERA`:** Foi implementado um regex para capturar dois padrões comuns de alteração: "redação dada por..." e "passa a vigorar com a seguinte alteração".
3.  **Detecção de `REVOGA`:** Após depuração, o `linker` foi capacitado a encontrar padrões como "Revogado pela Emenda Constitucional...".
4.  **Detecção de `REGULAMENTA` e `REMETE_A`:** O script foi expandido para incluir padrões como "Regulamentado pelo Decreto..." e "(Vide Lei...)".
5.  **Execução e Validação:** A execução final do `linker` identificou um total de 311 relações potenciais e criou com sucesso **110 arestas `[:ALTERA]`**, **136 `[:REVOGA]`**, **1 `[:REGULAMENTA]`** e **6 `[:REMETE_A]`**.

**Conclusão da Tarefa:** As tarefas 4.4 e 4.5 estão funcionalmente implementadas. O `linker` agora é uma ferramenta poderosa que enriquece o grafo com quatro tipos de relações normativas, extraídas diretamente dos textos legais.

---

### Data: 2025-10-13

**Tarefa:** 4.6 - Validar coerência temporal

**Detalhes:**

1.  **Criação do Validador:** Foi criado o diretório `temporal_validator/` com o script `validator.py` para realizar duas checagens de consistência de datas.
2.  **Checagem Interna:** Uma query SQL com `OVERLAPS` foi executada no PostgreSQL para garantir que não há versões do mesmo dispositivo com períodos de vigência sobrepostos. **Resultado: SUCESSO.**
3.  **Checagem Externa:** O script consultou as relações `[:ALTERA]` e `[:REVOGA]` no Neo4j e cruzou com as datas de publicação no PostgreSQL para garantir que nenhum ato "mais novo" estivesse sendo alterado por um "mais antigo". **Resultado: SUCESSO.**
4.  **Relatório Final:** O script gerou um relatório final "APROVADO", confirmando a coerência temporal dos dados no banco.

**Conclusão da Tarefa:** A tarefa 4.6 foi concluída com sucesso, aumentando a confiança na qualidade e integridade dos dados do projeto.

---

### Data: 2025-10-13

**Tarefa:** 4.7 - Implementar API de consulta de relações

**Detalhes:**

1.  **Criação da API:** Foi criado o diretório `api/` com um serviço FastAPI (`main.py`) e suas dependências.
2.  **Implementação do Endpoint:** Foi desenvolvido um endpoint `GET /atos/{urn}/relacoes` que se conecta ao Neo4j e consulta todas as relações de um determinado `AtoNormativo`.
3.  **Depuração:** A query Cypher inicial foi corrigida para usar `COALESCE` e retornar o `id_unico` para nós `:Dispositivo`, que não possuem URN, tornando a resposta da API mais completa.
4.  **Validação:** A API foi executada localmente com `uvicorn`, e o endpoint foi testado com sucesso usando `curl`, retornando a lista de relações para a Constituição Federal.

**Conclusão da Tarefa:** A tarefa 4.7 foi concluída. O projeto agora possui uma camada de serviço funcional para expor os dados do grafo, um passo essencial para a futura camada de RAG.

---

### Data: 2025-10-13

**Tarefa:** 4.8 - Gerar grafo de visualização (explorador)

**Detalhes:**

1.  **Ferramenta:** O Neo4j Browser, ferramenta web nativa do Neo4j e acessível em `http://localhost:7474`, foi definido como o explorador de grafo padrão para o projeto.
2.  **Uso:** A ferramenta permite a execução de consultas Cypher e renderiza os resultados de forma interativa, possibilitando a navegação visual entre os nós (`AtoNormativo`, `Dispositivo`) e as arestas (`CONTEM`, `ALTERA`, `REVOGA`, etc.).
3.  **Exemplo de Consulta:** Foi fornecida uma consulta de exemplo para visualizar a Constituição Federal e suas relações vizinhas: `MATCH path = (a:AtoNormativo {urn_lexml: 'br;federal;constituicao;1988-10-05'})-[*1..2]-() RETURN path`.

**Conclusão da Tarefa:** A tarefa 4.8 está concluída. O projeto dispõe de uma ferramenta de visualização robusta e funcional, que atende plenamente às necessidades de exploração e auditoria do grafo de conhecimento. O Bloco 4 está finalizado.

---

### Data: 2025-10-13

**Tarefa:** Implementar Catálogo de Fontes e Crawler de Emendas

**Detalhes:**

1.  **Decisão Arquitetural:** Atendendo a uma sugestão, foi decidido substituir o sistema de manifestos em arquivos `.json` por uma tabela `fonte_documento` no PostgreSQL, para servir como um catálogo de fontes centralizado e auditável.
2.  **Schema do Catálogo:** O arquivo `schema_postgres.sql` foi atualizado com a `CREATE TABLE` para `fonte_documento`, incluindo colunas para URN, URL, status (`PENDENTE`, `COLETADO`, `PROCESSADO`, `FALHA`), hash e metadados. O schema foi aplicado com sucesso ao banco de dados.
3.  **Desenvolvimento do Crawler:** Um novo módulo `crawler/` foi criado. O script `crawler/main.py` foi desenvolvido com duas funções principais:
    *   `--populate`: Consome a API de dados abertos da legislação de Goiás para popular a tabela `fonte_documento` com todas as Emendas Constitucionais, marcando-as como `PENDENTE`.
    *   `--process`: Busca por registros `PENDENTE`, baixa os PDFs correspondentes, calcula o hash SHA-256 e atualiza o status para `COLETADO`, salvando o caminho do arquivo local.
4.  **Execução e Validação:** O crawler foi executado com sucesso. A fase `--populate` inseriu **86 fontes** no catálogo. A fase `--process` baixou com sucesso **39 PDFs** e atualizou seus status, ignorando os itens que não possuíam link para download.

**Conclusão da Tarefa:** O sistema de ingestão foi significativamente aprimorado com a criação de um catálogo de fontes persistente e um crawler robusto. O projeto agora tem a capacidade de descobrir e coletar novas fontes de forma sistemática e auditável.

---

### Data: 2025-10-13

**Tarefa:** Criar e Depurar Orquestrador de Pipeline (`run_pipeline.py`)

**Detalhes:**

1.  **Criação do Orquestrador:** Foi criado o script `run_pipeline.py` na raiz do projeto. Seu objetivo é consultar a tabela `fonte_documento` por itens com status `COLETADO` e executar a sequência completa de processamento (`parser`, `normalizer`, `loader`, `integrity_checker`) para cada um.
2.  **Depuração Extensiva:** A execução do orquestrador revelou uma série de problemas que foram corrigidos iterativamente:
    *   **Caminhos de Arquivo:** A reorganização de pastas para o diretório `src/` invalidou os caminhos de output padrão nos scripts. O `run_pipeline.py` foi ajustado para passar os caminhos corretos como argumentos.
    *   **Erros de Importação e Variáveis:** Múltiplos `NameError`s foram corrigidos nos scripts (`argparse`, `setup_logger`, `TRIGGER_WORDS`, `hashlib`) devido a importações e definições de variáveis ausentes após as refatorações.
    *   **Formato de Data:** O `loader` falhava ao inserir datas no PostgreSQL. O script foi corrigido para converter as datas do formato `DD/MM/YYYY` para o padrão `YYYY-MM-DD` antes da inserção.
    *   **Idempotência do Neo4j:** O `integrity_checker` revelou que o `loader` estava duplicando nós no Neo4j em re-execuções. A lógica de `CREATE` foi substituída por `MERGE` para garantir a idempotência.
3.  **Execução Final:** Após todas as correções, o `run_pipeline.py` foi executado com sucesso para todas as fontes pendentes, processando-as e atualizando seus status para `PROCESSADO`.

**Conclusão da Tarefa:** O pipeline de ingestão agora é totalmente automatizado e robusto. O orquestrador `run_pipeline.py` é capaz de processar em lote novas fontes adicionadas pelo `crawler`, representando um marco de maturidade para a arquitetura do projeto.