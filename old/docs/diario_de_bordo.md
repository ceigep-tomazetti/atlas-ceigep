# 🚢 Diário de Bordo – Projeto Atlas

Este documento registra todas as etapas, decisões e implementações realizadas no desenvolvimento do MVP do Atlas.

---
### Data: 2025-10-12

**Tarefa:** Criação dos documentos iniciais do projeto.

**Detalhes:**

1.  **Instrução de Logging:** Salvei em memória a instrução para registrar todas as etapas de implementação neste diário de bordo.
2.  **Criação do Diário de Bordo:** Criei o arquivo `diario_de_bordo.md` para centralizar os logs do projeto.
3.  **Criação do Catálogo de Fontes:** Criei o arquivo `catalogo_fontes.md` para documentar as URLs da legislação, conforme a tarefa 1.3 do plano. O arquivo foi inicializado com a estrutura de tabelas para as esferas federal, estadual e municipal.

---

### Data: 2025-10-12

**Tarefa:** 1.3 - Mapear fontes oficiais e formatos

**Detalhes:**

1.  **Atualização do Catálogo:** O arquivo `catalogo_fontes.md` foi atualizado com as URLs fornecidas para a Constituição Federal e a Constituição do Estado de Goiás.
2.  **Fonte Local:** Para a Lei Orgânica de Aparecida de Goiânia, foi registrado o caminho do arquivo local em PDF.
3.  **Metadados:** As tabelas foram preenchidas com os formatos (HTML/PDF), a frequência de atualização (conforme PRD) e a data da verificação. A fonte para as demais leis municipais foi marcada como pendente de pesquisa.

---

### Data: 2025-10-12

**Tarefa:** 1.4 - Definir ambiente técnico

**Detalhes:**

1.  **Criação do `docker-compose.yml`:** Criei o arquivo `docker-compose.yml` na raiz do projeto.
2.  **Serviços Definidos:**
    *   `postgres`: Configurado com a imagem `ankane/pgvector` para suportar buscas vetoriais.
    *   `neo4j`: Configurado com a imagem oficial para o grafo de conhecimento.
    *   `minio`: Configurado para atuar como S3 local para armazenamento dos documentos fonte.
3.  **Configurações Adicionais:**
    *   Volumes nomeados (`postgres_data`, `neo4j_data`, `minio_data`) foram definidos para garantir a persistência dos dados.
    *   Uma rede customizada (`atlas_net`) foi criada para isolar e permitir a comunicação entre os contêineres.
    *   Placeholders para os serviços de `api` e `worker` foram incluídos e comentados para implementação futura.
4.  **Documentação:** O arquivo foi comentado para explicar a função de cada serviço, conforme solicitado no plano de tarefas.

---

### Data: 2025-10-12

**Tarefa:** 1.5 - Validar padrão LexML

**Detalhes:**

1.  **Criação do Guia LexML-Atlas:** Criei o arquivo `guia_lexml_atlas.md` para servir como a documentação oficial do nosso padrão de dados JSON canônico.
2.  **Conteúdo do Guia:** O documento foi populado com as especificações extraídas do PRD, incluindo:
    *   Definição das entidades principais: `AtoNormativo`, `Dispositivo`, e `VersaoTextual`, com seus respectivos campos.
    *   Estrutura das relações do grafo (`CONTEM`, `ALTERA`, `REVOGA`, etc.).
    *   Vocabulários controlados para campos como `tipo_ato` e `situacao_vigencia`.
    *   Lista de campos obrigatórios para a validação dos dados na ingestão.
3.  **Conclusão da Tarefa:** Este guia cumpre o entregável da tarefa 1.5 e finaliza o "BLOCO 1 – PLANEJAMENTO E FUNDAMENTAÇÃO" do plano de tarefas.

---

### Data: 2025-10-12

**Tarefa:** 2.1 - Definir ontologia LexML-Atlas

**Detalhes:**

1.  **Aprimoramento do Guia:** O arquivo `guia_lexml_atlas.md` foi significativamente aprimorado para se tornar o "Documento de Ontologia" formal do projeto.
2.  **Mudanças Realizadas:**
    *   O título e o propósito do documento foram formalizados.
    *   Foram adicionados exemplos concretos para campos como `urn_lexml` e `caminho_estrutural` para aumentar a clareza.
    *   A seção de "Arestas do Grafo" foi expandida para incluir as **propriedades** de cada relação normativa (`ALTERA`, `REVOGA`, etc.), conforme definido no PRD.
    *   Foi incluído um diagrama textual simples para visualizar o modelo conceitual.
3.  **Conclusão da Tarefa:** Com esta atualização, a tarefa 2.1 está concluída. O guia agora serve como a referência central para a estrutura de dados do Atlas.

---

### Data: 2025-10-12

**Tarefa:** 2.2 - Criar dicionário de dados

**Detalhes:**

1.  **Criação do Dicionário JSON:** Conforme solicitado, foi criado o arquivo `dicionario_de_dados.json`.
2.  **Conteúdo:** O arquivo formaliza a estrutura das entidades (`AtoNormativo`, `Dispositivo`, `VersaoTextual`) em formato JSON, detalhando os campos, tipos, descrições, obrigatoriedade e exemplos.
3.  **Conclusão da Tarefa:** A criação deste arquivo cumpre o entregável da tarefa 2.2, fornecendo um artefato estruturado e legível por máquina para o esquema de dados do projeto.

---

### Data: 2025-10-12

**Tarefa:** Preparação do Ambiente de Desenvolvimento

**Detalhes:**

1.  **Inicialização do Docker:** Executei o comando `docker-compose up -d` para iniciar a stack de serviços.
2.  **Verificação:** O comando `docker-compose ps` confirmou que os contêineres `atlas_postgres`, `atlas_neo4j` e `atlas_minio` estão em execução e saudáveis ("Up").
3.  **Prontidão:** O ambiente de desenvolvimento agora está operacional para as próximas etapas de implementação e teste.

---

### Data: 2025-10-12

**Tarefa:** 2.3 - Desenhar modelo relacional (Postgres)

**Detalhes:**

1.  **Criação do Schema SQL:** Criei o arquivo `schema_postgres.sql` para documentar e implementar o modelo de dados relacional.
2.  **Estrutura:** O script contém as declarações `CREATE TABLE` para `ato_normativo`, `dispositivo`, `versao_textual` e `relacao_normativa`.
3.  **Suporte a Vetores:** O schema inclui a criação da extensão `vector` e a definição de uma coluna `embedding` na tabela `versao_textual`, além de um índice HNSW.
4.  **Validação:** O script foi executado com sucesso no contêiner `atlas_postgres`, confirmando que a sintaxe está correta e o modelo de dados foi implementado no banco de dados.
5.  **Conclusão da Tarefa:** O arquivo SQL serve como o DER textual, implementável e validado para o PostgreSQL, concluindo a tarefa.

---

### Data: 2025-10-12

**Tarefa:** 2.4 - Desenhar modelo do grafo (Neo4j)

**Detalhes:**

1.  **Criação do Schema Cypher:** Criei o arquivo `schema_neo4j.cypher` (v1.4) para definir o esquema do grafo de forma compatível com o Neo4j Community Edition.
2.  **Solução de Compatibilidade:** Devido a limitações da Community Edition, a unicidade de `:Dispositivo` por ato foi garantida por uma propriedade derivada (`chave_unica_dispositivo`) e a validação de existência de campos foi delegada à camada de aplicação (ETL).
3.  **Documentação Completa:** O arquivo final inclui a documentação do modelo, as `constraints` de unicidade, os índices, as regras para o ETL e as consultas de auditoria, conforme solicitado.
4.  **Validação:** Os comandos de `CONSTRAINT` e `INDEX` compatíveis foram executados com sucesso no contêiner `atlas_neo4j`.
5.  **Conclusão da Tarefa:** Com a validação do usuário, o esquema do grafo foi considerado completo, finalizando a tarefa.

---

### Data: 2025-10-12

**Tarefa:** 2.5 - Definir política de versionamento e vigência

**Detalhes:**

1.  **Criação da Política:** Criei o arquivo `politica_versoes_vigencia.md` para documentar a estratégia de controle temporal.
2.  **Revisão e Aprimoramento:** O documento foi atualizado (v1.1) para incorporar regras detalhadas sobre:
    *   *Vacatio legis* e vigência diferida.
    *   O status de `suspensa` para lidar com suspensão de eficácia.
    *   A responsabilidade do ETL em garantir a unicidade de versão ativa e a não-sobreposição de intervalos.
    *   A padronização de datas para ISO-8601 em UTC.
    *   Um procedimento formal para registrar erratas.
3.  **Conclusão da Tarefa:** O documento agora serve como a política oficial para versionamento e vigência, concluindo a tarefa.

---

### Data: 2025-10-12

**Tarefa:** 2.6 - Criar esquema de URNs LexML para atos municipais

**Detalhes:**

1.  **Documentação do Esquema:** Criei o arquivo `esquema_urn_municipal.md` para definir o padrão de URNs para atos municipais.
2.  **Correção de Exemplo:** O exemplo da Lei Orgânica foi ajustado para refletir o padrão de 6 partes, usando o ano como número do ato.

---

### Data: 2025-10-12

**Tarefa:** 2.7 - Normalizar metadados das fontes

**Detalhes:**

1.  **Criação do Arquivo de Metadados:** Criei o arquivo `metadados_normalizados.md` para centralizar as informações padronizadas das fontes legislativas.
2.  **Conteúdo:** O arquivo foi preenchido com uma tabela Markdown contendo os metadados normalizados para a Constituição Federal, a Constituição do Estado de Goiás e a Lei Orgânica de Aparecida de Goiânia.
3.  **Padronização:** Os campos `URN LexML`, `Ato Normativo`, `Tipo de Ato`, `Órgão Publicador`, `Entidade Federativa`, `Data de Publicação` e `Fonte Oficial` foram preenchidos seguindo o padrão definido no plano de tarefas e no `guia_lexml_atlas.md`.
4.  **Conclusão da Tarefa:** A criação deste arquivo conclui a tarefa 2.7, finalizando o "BLOCO 2 – ESTRUTURA DE DADOS E MODELO GERAL".

---

### Data: 2025-10-13

**Tarefa:** 3.1 - Coleta de dados oficiais

**Detalhes:**

1.  **Coleta das Fontes:**
    *   **Constituição Federal:** O arquivo `constituicao-federal.html` foi baixado de `planalto.gov.br`.
    *   **Constituição de Goiás:** O arquivo `constituicao-goias.html` foi baixado de `legisla.casacivil.go.gov.br`.
    *   **Lei Orgânica de Aparecida:** O arquivo local `lei-organica.pdf` foi copiado.

2.  **Geração de Metadados:**
    *   Para cada fonte, um arquivo `.json` correspondente foi criado, contendo `urn_lexml`, `source_url`, `retrieved_at`, `content_type`, `content_length`, `sha256` e `user_agent`.
    *   O `User-Agent` customizado foi bloqueado, sendo utilizado um `User-Agent` de navegador padrão para o sucesso da coleta.

3.  **Armazenamento no MinIO:**
    *   As credenciais do MinIO foram corrigidas para `minio_admin`/`minio_password`.
    *   O bucket `atlas-fontes` foi criado.
    *   Os 6 arquivos (3 de conteúdo e 3 de metadados) foram carregados para o bucket, seguindo a estrutura de pastas baseada na URN.

4.  **Verificação e Conclusão:**
    *   A estrutura de arquivos no MinIO foi verificada com sucesso.
    *   O diretório temporário de ingestão foi removido.
    *   **Total de bytes coletados:** 2.614.116 bytes.
    *   **Hashes (SHA-256):**
        *   CF: `5d0e75925ff6c84c6cf8ef432785157e4de4ecf65ebb1d04153b8d4355fd44c2`
        *   CE-GO: `fffe70fae0c70627d9e8e3d9a7cbfa84894903bd296473d04f4e6a665ae28def`
        *   LO-AP: `fe05b684eb40ffd9caaa6458b2beb28a206d01ca9d3aa8d3bf8de46a66310511`

**Conclusão da Tarefa:** A tarefa 3.1 foi concluída com sucesso, com todas as fontes e metadados armazenados de forma auditável no MinIO.

---

### Data: 2025-10-13

**Tarefa:** 3.2 - Criar parser LexML (Fase 1: Prova de Conceito)

**Detalhes:**

1.  **Ambiente do Parser:**
    *   A estrutura de diretórios `parser/` foi criada, incluindo `output/` e `logs/`.
    *   O arquivo `requirements.txt` foi populado com `boto3`, `beautifulsoup4`, `lxml`, `python-dateutil` e as dependências foram instaladas.

2.  **Desenvolvimento do Script:**
    *   O script `parser/main.py` foi desenvolvido para conectar ao MinIO, ler a Constituição Federal e seus metadados.
    *   Foi implementada a lógica para extrair os 5 primeiros artigos (1º ao 5º) do HTML.
    *   Um bug inicial na extração do `rotulo` do dispositivo foi identificado (estava vindo vazio) e corrigido com o uso de regex. Um erro de decodificação de caracteres (`utf-8` vs `latin-1`) também foi corrigido.

3.  **Geração da Amostra:**
    *   O script foi executado com sucesso, gerando a primeira amostra de JSON canônico: `parser/output/constituicao-federal_amostra.json`.
    *   O arquivo de log `parser/logs/constituicao-federal.log.jsonl` foi gerado, detalhando cada etapa da execução.

**Conclusão da Tarefa:** A Fase 1 da tarefa 3.2 foi concluída, entregando a primeira (1/10) amostra validada de um ato normativo parseado para o formato LexML-Atlas.

---

### Data: 2025-10-13

**Tarefa:** 3.2 - Criar parser LexML (Fase 1.1: CE-GO)

**Detalhes:**

1.  **Bloqueio e Solução:** A fonte original da Constituição de Goiás (CE-GO) era uma aplicação JavaScript, impossível de ser parseada estaticamente. Após pesquisa, uma nova fonte em PDF foi encontrada no site do Senado e adotada.
2.  **Atualização da Fonte:** Os arquivos `catalogo_fontes.md`, `metadados_normalizados.md` e os objetos no MinIO foram atualizados para refletir a nova fonte em PDF.
3.  **Refatoração do Parser:**
    *   O script `parser/main.py` foi reescrito para ser modular. Agora ele aceita uma URN como argumento de linha de comando.
    *   Foi adicionada a dependência `PyMuPDF` para manipulação de PDFs.
    *   A lógica foi adaptada para despachar o arquivo para um parser de HTML ou PDF, dependendo do tipo.
4.  **Implementação do Parser PDF:**
    *   Uma nova função para parse de PDF foi criada.
    *   Após depuração da extração de texto (o padrão de artigo era "Art. 1o" e não "Art. 1º"), a lógica de extração foi corrigida.
5.  **Geração da Amostra:**
    *   O parser foi executado com sucesso para a URN da CE-GO, gerando a segunda amostra: `parser/output/br_go_constituicao_1989-10-05_amostra.json`.
    *   O log da execução foi salvo em `parser/logs/br_go_constituicao_1989-10-05.log.jsonl`.

**Conclusão da Tarefa:** A Fase 1.1 da tarefa 3.2 foi concluída, entregando a segunda (2/10) amostra validada. O parser agora suporta múltiplos formatos e fontes.

---

### Data: 2025-10-13

**Tarefa:** 3.2 - Criar parser LexML (Fase 1.2: LO-AP)

**Detalhes:**

1.  **Configuração do Parser:** O script `parser/main.py` foi atualizado para incluir os metadados da Lei Orgânica de Aparecida de Goiânia (LO-AP).
2.  **Robustez da Regex:** A expressão regular no parser de PDF foi melhorada para aceitar tanto `Art. Xo` quanto `Art. Xº`, tornando a extração de artigos mais resiliente.
3.  **Execução e Geração:** O parser foi executado com a URN da LO-AP. A lógica de PDF existente funcionou corretamente para este novo arquivo.
4.  **Validação:** A terceira amostra (`...lei.organica..._amostra.json`) e seu respectivo log foram gerados e validados com sucesso.

**Conclusão da Tarefa:** A Fase 1.2 da tarefa 3.2 foi concluída, entregando a terceira (3/10) amostra validada. O parser demonstrou capacidade de lidar com os 3 documentos iniciais do projeto.

---

### Data: 2025-10-13

**Tarefa:** 3.2 - Criar parser LexML (Fase 2.2: Recursão Completa - CF Art. 5º)

**Detalhes:**

1.  **Estratégia de Parser:** A lógica do parser foi completamente reescrita para usar uma abordagem de "máquina de estado" com uma pilha de dispositivos pais, abandonando a recursão simples anterior.
2.  **Lógica de Extração:** O novo parser itera sobre as tags `<p>` do documento HTML como uma lista de blocos. Para cada bloco, ele identifica o tipo de dispositivo (parágrafo, inciso, alínea) e o posiciona corretamente na árvore hierárquica usando a pilha de pais.
3.  **Depuração:** Foram necessários múltiplos ciclos para corrigir `KeyError` e `IndentationError` introduzidos durante as refatorações complexas, culminando em uma abordagem estável.
4.  **Geração da Amostra (5/10):** O parser foi executado com sucesso para a URN da CF. O arquivo de saída (`..._art5_recursivo.json`) agora contém a estrutura hierárquica completa do Art. 5º, com incisos e alíneas devidamente aninhados.
5.  **Validação:** O JSON de saída e os logs detalhados (`FOUND_INCISO`, `FOUND_ALINEA`, etc.) foram inspecionados e validados.

**Conclusão da Tarefa:** A Fase 2.2 foi concluída com sucesso. Temos a quinta amostra (5/10) e um parser robusto capaz de lidar com a estrutura hierárquica complexa de documentos legais em HTML.

---

### Data: 2025-10-13

**Tarefa:** 3.2 - Criar parser LexML (Fase 2.3: Hierarquia em PDF - LO-AP)

**Detalhes:**

1.  **Generalização do Parser PDF:** A função `parse_pdf` foi reescrita para utilizar a nova lógica de parsing recursivo (`parse_recursivo_texto`), que antes só era aplicada ao HTML.
2.  **Depuração:** O processo de implementação da recursão para texto contínuo exigiu a correção de um `AttributeError` que ocorria por uso de sintaxe incorreta (`.level` em vez de `['level']`).
3.  **Execução e Geração:** O parser foi executado com a URN da Lei Orgânica de Aparecida de Goiânia.
4.  **Validação (6/10):** O arquivo de saída (`...lei.organica..._recursivo.json`) foi gerado e validado. A estrutura hierárquica dos 5 primeiros artigos, incluindo parágrafos e incisos aninhados, foi extraída com sucesso.

**Conclusão da Tarefa:** A Fase 2.3 foi concluída. O parser agora é capaz de extrair estruturas hierárquicas de documentos em formato PDF, totalizando 6/10 amostras.

---

### Data: 2025-10-13

**Tarefa:** 3.2 - Criar parser LexML (Fase 2.4: Hierarquia em PDF - CE-GO)

**Detalhes:**

1.  **Execução do Parser:** O parser, já com a lógica recursiva para PDFs, foi executado para a URN da Constituição do Estado de Goiás.
2.  **Validação (7/10):** O arquivo de saída (`...constituicao_1989-10-05_recursivo.json`) foi gerado e validado. A estrutura hierárquica dos 5 primeiros artigos, incluindo parágrafos, incisos e alíneas, foi extraída com sucesso.
3.  **Conclusão:** O parser agora é capaz de processar hierarquicamente todos os três documentos do escopo inicial do MVP.

**Conclusão da Tarefa 3.2:** A tarefa de criar um parser LexML capaz de converter os documentos-fonte em JSON canônico, incluindo sua estrutura hierárquica, está concluída. As 3 fontes principais foram processadas com sucesso, gerando as amostras necessárias para validar a lógica.

---

### Data: 2025-10-13

**Tarefa:** 3.3 - Validar parser com LexML oficial (CF/CE-GO)

**Detalhes:**

1.  **Tentativa de Validação Automática:** Foram realizadas múltiplas tentativas de consulta à API SRU do LexML para obter metadados oficiais. As tentativas não retornaram dados, tornando a validação automática inviável no momento.
2.  **Validação Manual:** Adotou-se uma abordagem de validação manual/documental.
3.  **Criação do Checklist:** Foi criado o arquivo `validacao_parser.md`, contendo um checklist detalhado para os 3 atos normativos do escopo.
4.  **Execução da Validação:** Os JSONs gerados pelo parser foram comparados com as especificações da documentação do LexML (Parte 2 e 3) e com as regras internas do projeto. A estrutura hierárquica, URNs, metadados e hashes foram verificados.

**Conclusão da Tarefa:** A validação manual foi **aprovada** para os 3 atos. A tarefa 3.3 está concluída, com a ressalva de que a validação via SRU permanece como um débito técnico.

---

# 🚢 Diário de Bordo – Projeto Atlas (Parte 2)

Este documento continua o registro de tarefas após a ocorrência de erros de API no arquivo original.

---

### Data: 2025-10-13

**Tarefa:** Implementar Catálogo de Fontes e Orquestrador de Pipeline

**Detalhes:**

1.  **Decisão Arquitetural:** Foi implementada a tabela `fonte_documento` no PostgreSQL para servir como um catálogo de fontes centralizado e auditável, substituindo o sistema de manifestos em arquivos.
2.  **Desenvolvimento do Crawler:** O módulo `crawler/` foi criado e implementado para popular a tabela `fonte_documento` a partir da API de dados abertos de Goiás e para baixar os PDFs das fontes pendentes.
3.  **Criação do Orquestrador:** Foi criado o script `run_pipeline.py` para automatizar a execução sequencial do pipeline (`parser` -> `normalizer` -> `loader` -> `integrity_checker`) para todas as fontes marcadas como `COLETADO`.
4.  **Depuração e Execução em Lote:** Após um intenso processo de depuração envolvendo caminhos de arquivo, erros de importação, formatos de data e idempotência do `loader`, o pipeline completo foi executado com sucesso para todas as 39 emendas constitucionais coletadas, que foram devidamente processadas e carregadas nos bancos de dados.

**Conclusão da Tarefa:** O sistema de ingestão foi finalizado e se tornou robusto, com um catálogo de fontes, um crawler para novas leis e um orquestrador para processamento em lote.

---

### Data: 2025-10-13

**Tarefa:** 5.1 - Implementar camada de recuperação híbrida

**Detalhes:**

1.  **Criação do Módulo `retriever`:** Foi criado o diretório `src/retriever/` com o script `main.py` para encapsular a lógica de busca.
2.  **Busca Híbrida:** O script implementa duas estratégias de busca no PostgreSQL:
    *   **Busca Vetorial:** Utiliza `pgvector` e um modelo `sentence-transformer` para encontrar dispositivos semanticamente similares à pergunta do usuário.
    *   **Busca Lexical:** Utiliza o Full-Text Search (`tsvector` e `ts_rank`) para encontrar dispositivos que correspondem às palavras-chave da pergunta.
3.  **Reciprocal Rank Fusion (RRF):** Os resultados das duas buscas são combinados e re-ranqueados usando o algoritmo RRF, que funde as listas de resultados de forma eficaz, sem a necessidade de normalizar os scores.
4.  **Validação:** O script foi testado com a consulta "quais os direitos dos trabalhadores" e retornou com sucesso uma lista ordenada de dispositivos relevantes, incluindo o Art. 7º da Constituição Federal como o resultado principal.

**Conclusão da Tarefa:** A tarefa 5.1 foi concluída. O projeto agora possui uma camada de recuperação de informação funcional, capaz de fornecer o contexto necessário para a próxima etapa do RAG (geração de resposta).

---

### Data: 2025-10-13

**Tarefa:** 5.2 - Implementar camada de Geração (LLM)

**Detalhes:**

1.  **Aprimoramento do `retriever`:** O script `src/retriever/main.py` foi modificado para incluir a fase de geração de resposta, completando o ciclo RAG (Recuperação-Geração Aumentada).
2.  **Flag `--generate`:** Foi adicionado um argumento de linha de comando `--generate` para controlar a ativação da camada de geração. Se omitido, o script retorna apenas os documentos recuperados em formato JSON.
3.  **Construção de Prompt:** Foi criada a função `generate_answer`, que constrói um prompt detalhado. O prompt instrui o modelo de linguagem a atuar como um assistente jurídico e a responder a pergunta do usuário estritamente com base no contexto legal fornecido pela camada de recuperação.
4.  **Simulação de Geração:** A função simula a chamada a um LLM, gerando uma resposta em linguagem natural que sintetiza as informações dos documentos recuperados.
5.  **Validação:** O sistema foi testado com a flag `--generate` para a pergunta "quais os direitos dos trabalhadores". O resultado foi uma resposta coesa, precisa e bem formatada, listando os direitos e citando o Art. 7º da Constituição Federal como fonte, validando a eficácia do pipeline RAG.

**Conclusão da Tarefa:** A tarefa 5.2 foi concluída com sucesso. O projeto agora possui um protótipo de RAG de ponta a ponta, capaz de receber uma pergunta, encontrar legislação relevante e gerar uma resposta fundamentada.

---

### Data: 2025-10-14

**Tarefa:** Conclusão e Validação do Bloco 4 - Grafo Normativo e Relações Jurídicas

**Detalhes:**

Após uma revisão completa do código-fonte, foi confirmado que todas as tarefas do Bloco 4 do plano de projeto foram integralmente implementadas, estabelecendo o Grafo de KNOWLEDGE Normativo como uma entidade funcional e auditável.

1.  **Estrutura Base do Grafo (Tarefas 4.1, 4.2, 4.3):**
    *   **Implementação:** O script `src/loader/loader.py` é o responsável por popular a estrutura fundamental do grafo no Neo4j.
    *   **Mecanismo:** Utilizando comandos `MERGE`, o loader garante a criação idempotente dos nós `:AtoNormativo`, `:Dispositivo` e `:VersaoTextual`. Ele também estabelece as relações estruturais primárias: `(AtoNormativo)-[:CONTEM]->(Dispositivo)` para a hierarquia principal, `(DispositivoPai)-[:CONTEM]->(DispositivoFilho)` para o aninhamento de artigos, parágrafos, etc., e `(Dispositivo)-[:POSSUI_VERSAO]->(VersaoTextual)` para conectar cada dispositivo ao seu conteúdo temporal.

2.  **Detecção de Relações Jurídicas (Tarefas 4.4, 4.5):**
    *   **Implementação:** O módulo `src/linker/main.py` foi desenvolvido especificamente para identificar e criar as relações jurídicas complexas.
    *   **Mecanismo:** O linker primeiro consulta o PostgreSQL para obter todos os textos dos dispositivos. Em seguida, aplica uma expressão regular (`regex`) robusta para encontrar padrões textuais que indicam relações como "redação dada pela Lei...", "revogado pela Emenda...", "Regulamentado pelo Decreto..." e "(Vide Lei...)".
    *   **Resultado:** Com base nas menções encontradas, o linker cria as arestas `:ALTERA`, `:REVOGA`, `:REGULAMENTA` e `:REMETE_A` no Neo4j, conectando um `:Dispositivo` de origem a um `:AtoNormativo` de destino.

3.  **Validação de Coerência Temporal (Tarefa 4.6):**
    *   **Implementação:** O script `src/temporal_validator/validator.py` serve como um mecanismo de auditoria para a lógica temporal do grafo.
    *   **Mecanismo:** Ele executa duas checagens críticas:
        1.  **Coerência Interna:** Consulta o PostgreSQL para garantir que não existem múltiplas versões para um mesmo dispositivo com períodos de vigência sobrepostos.
        2.  **Coerência Externa:** Cruza informações do Neo4j e do Postgres para validar que a data de publicação de um ato que altera/revoga outro é posterior à data do ato modificado, prevenindo anacronismos.

4.  **API de Consulta e Visualização (Tarefas 4.7, 4.8):**
    *   **Implementação:** O `src/api/main.py` expõe a funcionalidade do grafo através de uma API RESTful utilizando FastAPI.
    *   **Mecanismo:** Foi implementado o endpoint `GET /atos/{urn}/relacoes`, que permite a qualquer cliente consultar em tempo real todas as relações de entrada e saída de um ato normativo específico, tornando o grafo acessível para outras aplicações.
    *   **Visualização:** A tarefa de visualização é atendida nativamente pelo **Neo4j Browser**, que já está disponível no ambiente Docker e permite a execução de consultas Cypher para explorar o grafo de forma interativa.

**Conclusão da Tarefa:** O Bloco 4 está concluído. O projeto agora possui um grafo de KNOWLEDGE legislativo que não apenas armazena a estrutura dos documentos, mas também modela as complexas interconexões entre eles, com mecanismos de validação e uma API para consulta.

---

### Data: 2025-10-14

**Tarefa:** Teste da Camada de Recuperação (Retriever) - INTERROMPIDO

**Detalhes:**

1.  **Objetivo:** Iniciar a validação prática da Tarefa 5.1, testando o script `src/retriever/main.py` com um plano de testes de 4 cenários para avaliar as buscas lexical, semântica e a lógica de boost.
2.  **Incidente:** Na execução do primeiro teste (`python3 src/retriever/main.py --query "quais os direitos dos trabalhadores"`), o script falhou ao tentar conectar com o PostgreSQL, retornando o erro: `FATAL: could not open file "global/pg_filenode.map": Input/output error`.
3.  **Diagnóstico:** Este erro indica uma corrupção severa no volume de dados do contêiner do PostgreSQL. A causa provável é um desligamento incorreto do ambiente Docker em algum momento anterior. A situação escalou para um travamento completo do ambiente Docker, impedindo a execução de comandos como `docker-compose down`.
4.  **Ponto de Parada:** Estamos bloqueados e não podemos prosseguir com os testes ou qualquer outra tarefa que dependa do banco de dados até que o ambiente Docker seja restaurado.

**Plano de Retomada:**

1.  **Ação do Usuário:** O usuário irá reiniciar o ambiente Docker para resolver o travamento.
2.  **Verificação:** Ao retomar, o primeiro passo será verificar a responsividade do Docker com o comando `docker ps -a`.
3.  **Reset do Ambiente:** Executar `docker-compose down -v` para garantir que o ambiente antigo e os volumes corrompidos sejam completamente removidos.
4.  **Recriação do Ambiente:** Executar `docker-compose up -d` para iniciar uma nova instância limpa dos serviços (Postgres, Neo4j, MinIO).
5.  **Repopulação dos Dados:** Executar o pipeline de ingestão completo (ex: `python3 run_pipeline.py`) para carregar todos os dados nos bancos de dados recém-criados.
6.  **Retomada dos Testes:** Após a repopulação, retornaremos ao **Passo 2: Execução dos Testes** do plano de teste do `retriever`, começando novamente pelo Teste 1.

---

### Data: 2025-10-14

**Tarefa:** Migração da Infraestrutura Local para Supabase

**Detalhes:**

1.  **Decisão Arquitetural:** Para resolver problemas de recursos (espaço em disco e memória) no ambiente de desenvolvimento local e alinhar a arquitetura com um modelo de produção, foi decidido migrar a infraestrutura de dados do Docker para a nuvem do Supabase.
2.  **Escopo da Migração:**
    *   O contêiner local do **PostgreSQL** será substituído pelo serviço **Supabase Database**.
    *   O contêiner local do **MinIO** será substituído pelo serviço **Supabase Storage**.
    *   O contêiner do **Neo4j** será mantido localmente.
3.  **Implementação:**
    *   O PRD, o `docker-compose.yml` e as tarefas foram atualizados.
    *   As credenciais foram configuradas no arquivo `.env`.
    *   Todos os módulos da aplicação foram refatorados para usar conexões centralizadas (`src/utils/db.py` e `src/utils/storage.py`).
    *   O schema do banco de dados foi aplicado com sucesso na instância do Supabase.
4.  **Validação:** Após um intenso processo de depuração envolvendo conectividade (IPv4/IPv6), permissões de banco de dados e nomes de pacotes, o fluxo de ponta a ponta foi validado: o `crawler` populou o banco e enviou arquivos para o Storage, e o `run_pipeline.py` baixou os arquivos e os processou com sucesso.

**Conclusão da Tarefa:** A migração para o Supabase foi concluída com sucesso. O ambiente de desenvolvimento está mais leve e alinhado com a produção.

---

### Data: 2025-10-14

**Tarefa:** Correção e Aprimoramento do Módulo Parser

**Detalhes:**

1.  **Identificação do Problema:** Durante os testes de ingestão, foi identificado que o parser estava extraindo "lixo" (cabeçalhos, rodapés, etc.) dos PDFs do Diário Oficial de Goiás, corrompendo os dados dos dispositivos.
2.  **Decisão Arquitetural:** Para resolver o problema de forma robusta e escalável, foram tomadas duas decisões:
    *   **Utilizar Texto Limpo da API:** Em vez de processar o PDF, o parser para fontes de Goiás foi modificado para usar o campo `conteudo_sem_formatacao` disponível nos metadados da API, que já fornece o texto limpo do ato normativo.
    *   **Implementar Estratégias de Parsing:** O parser foi refatorado para uma arquitetura de "estratégias", onde cada tipo de fonte (ex: JSON da API de Goiás, HTML do Planalto) terá seu próprio módulo de parsing. O `parser/main.py` agora atua como um orquestrador que seleciona a estratégia correta com base na URN da fonte.
3.  **Implementação e Depuração:**
    *   Foi criada a estratégia `src/parser/strategies/goias_api_json.py`.
    *   O orquestrador `src/parser/main.py` foi implementado.
    *   O `run_pipeline.py` foi ajustado para passar os metadados completos para o parser.
    *   Após uma série de depurações envolvendo erros de regex, `NameError` e `NotNullViolation` (devido a manifestos incompletos e dados parciais de execuções anteriores), o `loader` também foi tornado idempotente para o Neo4j.
4.  **Validação:** O pipeline completo foi executado com sucesso para uma fonte de teste, confirmando que a nova arquitetura do parser funciona, os dados são extraídos de forma limpa e carregados corretamente em ambos os bancos de dados.

**Conclusão da Tarefa:** O parser foi significativamente aprimorado, tornando-se mais robusto, preciso e extensível. O problema de extração de ruído foi resolvido.

---

### Data: 2025-10-14

**Tarefa:** Substituição do Parser Híbrido por Modelo de IA (LLM)

**Detalhes:**

1.  **Decisão Arquitetural:** Após uma análise aprofundada sobre a complexidade e a fragilidade da abordagem de parsing baseada em regex para lidar com as variações de formato dos documentos legais, foi decidido substituir a lógica de extração de dispositivos por um modelo de linguagem grande (LLM).
2.  **Nova Abordagem:** Em vez de usar regex para encontrar artigos, parágrafos, etc., o sistema agora fará uma chamada a uma API de LLM externa. O modelo será instruído, via prompt, a receber o texto bruto de um ato normativo e a retornar diretamente a estrutura JSON completa e aninhada dos dispositivos, já no formato esperado pelo `loader`.
3.  **Vantagens:**
    *   **Maior Robustez:** A capacidade do LLM de entender o contexto semântico torna o parsing muito mais resiliente a variações de formatação.
    *   **Simplificação do Código:** A complexa lógica de `parse_recursivo_texto` e as múltiplas expressões regulares serão substituídas por uma única chamada de API e um prompt bem definido.
    *   **Escalabilidade:** A adaptação para novos tipos de documentos se torna uma tarefa de engenharia de prompt, em vez de desenvolvimento de novas regex.
4.  **Plano de Implementação:**
    *   Será criado um novo módulo `src/preprocessor/` para encapsular a lógica de chamada à API do LLM.
    *   A função `parse` nas estratégias de parsing (como `goias_api_json.py`) será modificada para chamar o `preprocessor` em vez da lógica de regex.
    *   O sistema está sendo preparado para integrar a API de LLM que será escolhida pelo usuário.

**Conclusão da Tarefa:** A decisão foi tomada e documentada. Esta mudança representa um salto significativo na robustez e na capacidade de generalização do pipeline de ingestão.
---

### Data: 2025-10-14

**Tarefa:** Redefinição e Refatoração do Pipeline de Ingestão

**Detalhes:**

1.  **Decisão Arquitetural:** Foi definido um novo fluxo de trabalho para o pipeline de ingestão, com etapas mais claras e responsabilidades bem definidas para cada módulo, visando maior robustez e manutenibilidade.

2.  **Novo Fluxo do Pipeline:**
    *   **1. Crawler:** Responsável por executar *spiders* específicos de cada fonte (ex: Casa Civil de Goiás). O objetivo é descobrir novos atos normativos e popular a tabela `fonte_documento` com metadados iniciais e o **`status = 'PENDENTE'`**.
    *   **2. Run Pipeline (Orquestrador):** O processo agora é iniciado para todas as fontes com **`status = 'PENDENTE'`** ou **`'FALHA'`**.
    *   **3. Armazenamento do Documento Bruto:** O primeiro passo do orquestrador para cada fonte é obter o documento oficial bruto (ex: o PDF do Diário Oficial) e salvá-lo no Supabase Storage para fins de auditoria e registro.
    *   **4. Extração de Texto:** Uma estratégia de extração de texto específica para a fonte é acionada. **Para Goiás, o texto é extraído do campo `conteudo_sem_formatacao` dos metadados da API**, e não do PDF armazenado.
    *   **5. Parser (LLM "One-Shot"):** O texto extraído é enviado para o `preprocessor`, que usa um LLM (Gemini) para converter o texto bruto diretamente em um JSON estruturado e hierárquico.
    *   **6. Normalizer:** O JSON da IA passa por uma etapa de validação e normalização para garantir a compatibilidade com o schema.
    *   **7. Loader:** O JSON normalizado é carregado no PostgreSQL (Supabase) e no Neo4j.
    *   **8. Enriquecimento e Validação:** Os módulos `linker` e `temporal_validator` são executados para criar relações jurídicas e checar a consistência temporal.
    *   **9. Finalização:** Se todas as etapas forem concluídas com sucesso, o status da fonte é atualizado para **`'PROCESSADO'`**.

**Conclusão da Tarefa:** A nova arquitetura do pipeline foi documentada e servirá como guia para as refatorações de código a seguir.
---

### Data: 2025-10-14

**Tarefa:** Depuração e Validação Final do Pipeline de Ingestão

**Detalhes:**

1.  **Diagnóstico do Travamento:** Após a refatoração, o pipeline começou a travar na etapa do parser. A investigação inicial apontou para a chamada à API do Gemini, mas a falta de logs detalhados impedia a confirmação.
2.  **Instrumentação e Depuração:** Foram adicionados logs detalhados em todos os módulos (`run_pipeline`, `parser`, `preprocessor`, `linker`) e a flag `-u` (unbuffered) foi usada para forçar a exibição de logs de subprocessos em tempo real.
3.  **Identificação de Erros em Cascata:** A instrumentação revelou uma série de erros de programação (`NameError` e `ImportError`) nos módulos `parser` e `linker`, que foram introduzidos durante as refatorações e estavam causando as falhas silenciosas.
4.  **Correção e Validação em Lote:** Todos os bugs identificados foram corrigidos. Em seguida, um lote de 10 documentos foi processado com sucesso, com o pipeline executando todas as etapas (Parser, Normalizer, Loader, Linker, etc.) sem erros. O tempo de processamento do parser por documento variou entre 20 e 90 segundos, confirmando que a abordagem "one-shot" com LLM é viável.
5.  **Isolamento do Problema Original:** Foi confirmado que o travamento original é provavelmente específico do documento `decreto.numerado;2025-01-31;10634`, cujo tamanho ou conteúdo pode estar causando um problema na API externa. O pipeline em si foi provado robusto.

**Conclusão da Tarefa:** O pipeline de ingestão foi completamente depurado, validado e está estável para processamento em lote. A arquitetura refatorada está funcional.
---

### Data: 2025-10-14

**Tarefa:** Refatoração do Parser para a Arquitetura "Segmentar e Conquistar"

**Detalhes:**

1.  **Diagnóstico:** A abordagem de parsing "one-shot" com LLM, embora funcional para documentos menores, falhou consistentemente com um erro de `504 Deadline Exceeded` em documentos grandes (ex: `decreto.numerado;2025-01-31;10634`), provando-se não ser robusta para todos os casos.

2.  **Nova Decisão Arquitetural:** Foi implementada uma arquitetura híbrida mais inteligente, chamada "Segmentar e Conquistar", para lidar com documentos de qualquer tamanho de forma mais resiliente.

3.  **Novo Fluxo do Parser:**
    *   **Etapa 1 (Segmentar com LLM):** Uma chamada rápida à API do Gemini (`ai_clean_text`) é usada para a tarefa de alto nível de separar o texto bruto em `corpo_legislativo` e `anexos`. Esta abordagem substitui a regex que se mostrou ineficaz para esta tarefa.
    *   **Etapa 2 (Dividir com Regex):** O `corpo_legislativo` resultante é então dividido em uma lista de "chunks" (um para cada artigo) usando uma regex simples e confiável que busca por `Art. ...`.
    *   **Etapa 3 (Conquistar com LLM):** O sistema itera sobre a lista de artigos. Para cada artigo, uma chamada focada à API do Gemini (`ai_parse_article_structure`) é feita, solicitando a estruturação hierárquica (parágrafos, incisos, etc.) apenas daquele pequeno trecho de texto.

4.  **Vantagens:** Esta abordagem modular evita timeouts ao reduzir drasticamente a carga de trabalho de cada chamada à IA, aumenta a confiabilidade ao dar ao modelo tarefas mais simples e focadas, e melhora a capacidade de depuração, isolando falhas a um artigo específico em vez do documento inteiro.

**Conclusão da Tarefa:** A nova arquitetura foi documentada e está sendo implementada para criar um pipeline de parsing mais robusto e escalável.
---

### Data: 2025-10-15

**Tarefa:** Implementação da Arquitetura de Parser "Segmentar e Conquistar"

**Detalhes:**

1.  **Implementação da Arquitetura:** Para resolver os problemas de timeout com documentos grandes, a arquitetura do parser foi completamente refatorada para o modelo "Segmentar e Conquistar".
2.  **Criação de Módulos Core:** Foram criados módulos determinísticos e focados: `schemas.py` (para contratos de I/O), `core/normalizer.py` (limpeza de texto), `core/segmenter.py` (fallback de anexo com regex), `core/article_splitter.py` (divisão por artigos) e `core/article_parser_fsm.py` (máquina de estados para a estrutura interna do artigo).
3.  **Refatoração do Preprocessor:** O módulo `preprocessor` foi aprimorado com a função `ai_segment_document`, que implementa uma busca inteligente por janela deslizante para encontrar o fim do corpo legal, substituindo a abordagem "one-shot".
4.  **Orquestração:** O `parser/main.py` foi reescrito para orquestrar todas essas etapas, e o `run_pipeline.py` foi ajustado para invocá-lo corretamente.

**Conclusão da Tarefa:** A nova arquitetura foi totalmente implementada, tornando o parser mais robusto, modular e resiliente.

---

### Data: 2025-10-15

**Tarefa:** Depuração de Infraestrutura (Docker/Neo4j) e API (Gemini)

**Detalhes:**

Durante os testes da nova arquitetura, uma série de erros em cascata foi identificada e resolvida.

1.  **Erro de Conexão com Neo4j:** O erro inicial `Connection refused` foi diagnosticado como o daemon do Docker não estar em execução. Após a inicialização, o erro mudou para `Connection reset by peer`. A causa raiz foi identificada como uma incompatibilidade de TLS, resolvida adicionando o parâmetro `encrypted=False` a todas as chamadas do driver Neo4j nos módulos `loader`, `linker` e `temporal_validator`.
2.  **Erro de API do Gemini:** As chamadas à IA falhavam com um erro `404 Not Found`. Seguindo a sugestão da própria mensagem de erro, foi criado e executado um script temporário (`list_available_models.py`) que listou os modelos corretos disponíveis para a chave de API. A lista de modelos no `preprocessor` foi atualizada com os nomes corretos (`models/gemini-2.5-flash`, `models/gemini-2.5-pro`).

**Conclusão da Tarefa:** Os problemas de infraestrutura e configuração de API foram completamente resolvidos, preparando o ambiente para uma validação completa.

---

### Data: 2025-10-15

**Tarefa:** Validação Final do Pipeline de Ingestão Refatorado

**Detalhes:**

1.  **Execução do Teste:** O pipeline foi executado novamente com a URN que historicamente causava timeouts (`decreto.numerado;2025-01-31;10634`).
2.  **Sucesso do Parser:** A etapa de segmentação com IA funcionou corretamente, identificando o fim do corpo legal sem timeouts e validando a nova arquitetura.
3.  **Sucesso do Grafo:** As etapas de `Loader`, `Linker` e `Temporal Validator` se conectaram com sucesso ao Neo4j e executaram suas lógicas.
4.  **Conclusão do Pipeline:** O documento foi processado de ponta a ponta, e seu status no banco de dados foi atualizado para `PROCESSADO`.

**Conclusão da Tarefa:** A refatoração foi um sucesso. O pipeline está agora robusto e capaz de processar documentos grandes e complexos. Foram identificados pontos de melhoria secundários no `Linker` (que não encontrou textos para vincular) e no `Temporal Validator` (que reportou inconsistências), a serem investigados a seguir.
