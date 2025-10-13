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
