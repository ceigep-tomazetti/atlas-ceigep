# 🧩 PLANO DE TAREFAS – ATLAS MVP

**Versão:** 1.1
**Horizonte:** 30 dias (Sprint 1)
**Base:** PRD do Atlas (LexML-first com grafo e RAG)
**Metodologia:** 6 blocos macro (Planejamento, Estrutura, Ingestão, Grafo, Avaliação, Migração)

---

## 🧱 BLOCO 1 – PLANEJAMENTO E FUNDAMENTAÇÃO

| Nº  | Tarefa                                        | Objetivo                                                              | Entregável de Conclusão                                                            | Status                                                           |
| --- | --------------------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 1.2 | Confirmar escopo legal (CF, CE-GO, Aparecida) | Fixar corpus e limites do MVP                                         | Lista validada de atos (IDs, títulos, URLs oficiais)                               | Em execução — base estadual priorizada via API JSON, municipal parcial |
| 1.3 | Mapear fontes oficiais e formatos             | Identificar URLs, formatos (PDF/HTML/XML) e frequência de atualização | **Catálogo de Fontes** (planilha com 100% dos links e datas de última atualização) | Em execução — catálogo agora na tabela Supabase `fonte_documento` (base estadual completa; municipal em andamento) |
| 1.4 | Definir ambiente técnico                      | Padronizar stack (Supabase + Docker), portas, volumes e redes         | Arquivo `docker-compose.yml` e `.env` validados e documentados                     | Concluída — ambiente Docker usa Neo4j local + Supabase; .env padronizado           |
| 1.5 | Validar padrão LexML                          | Revisar estrutura XML e schema de referência                          | **Guia interno LexML Atlas**, resumindo tags e campos obrigatórios                 | Pendente                                                         |

---

## 🧩 BLOCO 2 – ESTRUTURA DE DADOS E MODELO GERAL

| Nº  | Tarefa                                           | Objetivo                                                        | Entregável de Conclusão                                                    |
| --- | ------------------------------------------------ | --------------------------------------------------------------- | -------------------------------------------------------------------------- |
| 2.1 | Definir **ontologia LexML-Atlas**                | Formalizar os tipos de nós e arestas que comporão o grafo       | **Documento de Ontologia** (entidades + propriedades + vocabulários PT-BR) |
| 2.2 | Criar **dicionário de dados**                    | Definir nomes de campos, tipos, descrições e formatos           | **Dicionário Atlas v1** em tabela JSON/Markdown                            |
| 2.3 | Desenhar **modelo relacional (Postgres)**        | Estruturar tabelas de atos, dispositivos, versões, relações     | Diagrama entidade-relacionamento (DER) validado                            |
| 2.4 | Desenhar **modelo do grafo (Neo4j)**             | Estruturar nós e relações LexML-first                           | Esquema do grafo (nós, arestas, propriedades)                              |
| 2.5 | Definir política de versionamento e vigência     | Garantir rastreabilidade temporal e hash por versão             | Documento “Controle de Versões e Vigência”                                 |
| 2.6 | Criar esquema de URNs LexML para atos municipais | Uniformizar identificação de leis de Aparecida                  | Lista de URNs padronizadas + script de geração automática                  |
| 2.7 | Normalizar metadados das fontes                  | Padronizar “órgão publicador”, “tipo de ato”, “data publicação” | Planilha consolidada com 100% das leis normalizadas                        |

---

## ⚙️ BLOCO 3 – INGESTÃO, NORMALIZAÇÃO E INDEXAÇÃO

| Nº  | Tarefa                                         | Objetivo                                                     | Entregável de Conclusão                                     |
| --- | ---------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------- |
| 3.1 | **Coleta de dados oficiais**                   | Baixar e armazenar as fontes oficiais (CF, CE-GO, Aparecida) | Bucket Supabase `/fontes-documentos` com 100% dos arquivos + log de coleta |
| 3.2 | Criar **parser LexML**                         | Converter PDF/HTML/XML em JSON canônico LexML                | 10 amostras parseadas e validadas                           |
| 3.3 | Validar parser com LexML oficial (CF/CE-GO)    | Testar consistência estrutural e tags                        | Checklist 100% OK em 20 atos                                |
| 3.4 | Implementar **normalizador**                   | Limpar, corrigir e segmentar texto por dispositivos          | 100 leis normalizadas + relatório de offsets                |
| 3.5 | Criar **pipeline de carga (ETL)**              | Inserir JSON no Supabase DB e Neo4j com logs                 | Execução única com logs e contadores de sucesso/falha       |
| 3.6 | Criar rotina de **verificação de integridade** | Confirmar URNs, hashes, contagem de dispositivos             | Relatório “Ingestão e Integridade” (totais e % válidos)     |
| 3.7 | Gerar **embeddings por dispositivo**           | Preparar base semântica para RAG                             | Índice vetorial (pgvector) com 100% dos dispositivos        |
| 3.8 | Criar **índices BM25**                         | Permitir busca lexical paralela                              | Índices de texto em Postgres prontos                        |
| 3.9 | Testar pipeline completo                       | Validar execução contínua do início ao fim                   | Log de pipeline executado com zero falhas críticas          |

---

## 🔗 BLOCO 4 – GRAFO NORMATIVO E RELAÇÕES JURÍDICAS

| Nº  | Tarefa                                       | Objetivo                                           | Entregável de Conclusão                               |
| --- | -------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------- |
| 4.1 | Criar esquema base no Neo4j                  | Instanciar nós (AtoNormativo, Dispositivo, Versão) | Estrutura inicial com 10 atos carregados              |
| 4.2 | Implementar mapeamento “CONTÉM”              | Relacionar atos → dispositivos                     | 100% dos dispositivos conectados ao respectivo ato    |
| 4.3 | Implementar “POSSUI_VERSAO”                  | Relacionar dispositivos → versões                  | 100% dos dispositivos com versão vigente              |
| 4.4 | Detectar e registrar relações ALTERA/REVOGA  | Identificar citações explícitas nos textos         | 80% das relações identificadas + log de confiança     |
| 4.5 | Criar relações REGULAMENTA e REMETE_A        | Mapear menções CF↔CE↔Municipal                     | Tabela de remissões com referência cruzada            |
| 4.6 | Validar coerência temporal                   | Garantir que vigência não conflite entre versões   | Relatório “Coerência Temporal” aprovado               |
| 4.7 | Implementar API de consulta de relações      | Permitir query direta no grafo (REST/GraphQL)      | Endpoint funcional `GET /atos/{urn}/relacoes`         |
| 4.8 | Gerar **grafo de visualização** (explorador) | Exibir conexões e hierarquias                      | Gráfico navegável (pelo Neo4j Browser ou export JSON) |

---

## 🧠 BLOCO 5 – RECUPERAÇÃO E RAG (Consulta e Resposta)

| Nº  | Tarefa                                        | Objetivo                                                  | Entregável de Conclusão                        |
| --- | --------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------- |
| 5.1 | Implementar camada de **recuperação híbrida** | Combinar BM25 e embeddings para contexto                  | Script de recuperação com ranking integrado    |
| 5.2 | Criar **montagem de contexto LexML**          | Montar contexto por dispositivo (texto + metadados + URN) | 10 exemplos revisados e corretos               |
| 5.3 | Desenvolver **motor de geração (modelo)**     | Gerar respostas com citação e contexto                    | Saída formatada com pinpoint e URL             |
| 5.4 | Aplicar **política de confiança e “não sei”** | Evitar respostas incertas ou ambíguas                     | Respostas com limiar de confiança aplicado     |
| 5.5 | Validar 50 perguntas de teste                 | Avaliar precisão e qualidade de respostas                 | Relatório de desempenho (métricas e amostras)  |
| 5.6 | Ajustar parâmetros e thresholds               | Melhorar precisão e recall                                | Versão final dos pesos e thresholds            |
| 5.7 | Gerar **relatório de QA final**               | Consolidar desempenho e achados                           | Documento de qualidade (≥85% precisão factual) |

---

## ☁️ BLOCO 6 – MIGRAÇÃO PARA SUPABASE

| Nº  | Tarefa                                               | Objetivo                                                              | Entregável de Conclusão                                                              |
| --- | ---------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 6.1 | Configurar Variáveis de Ambiente para Supabase       | Centralizar credenciais de acesso ao banco de dados e storage          | Arquivo `.env` com placeholders para todas as chaves Supabase.                       |
| 6.2 | Refatorar Conexão com Banco de Dados                 | Modificar todos os módulos para conectar ao Supabase DB remoto        | Função de conexão unificada que utiliza as variáveis de ambiente.                    |
| 6.3 | Refatorar Módulos de Armazenamento                   | Substituir I/O de arquivos locais por uploads/downloads no Supabase Storage | Crawler faz upload, pipeline faz download; coluna `caminho_arquivo_local` atualizada. |
| 6.4 | Remover Serviços Locais do Docker Compose            | Aliviar o ambiente de desenvolvimento local                           | Arquivo `docker-compose.yml` sem os serviços `postgres` e `minio`.                   |
| 6.5 | Criar e Executar Script de Migração de Schema        | Preparar a instância remota do Supabase com as tabelas necessárias    | Script `run_migrations.py` que aplica os arquivos de `migrations/` em ordem.         |
| 6.6 | Testar Pipeline de Ingestão com Supabase             | Validar o fluxo completo de ponta a ponta com a nova infraestrutura   | Execução do `run_pipeline.py` sem erros, com dados persistidos no Supabase.          |

---

## 🚀 BLOCO 7 – ENTREGA E TRANSIÇÃO

| Nº  | Tarefa                                  | Objetivo                                      | Entregável de Conclusão                        |
| --- | --------------------------------------- | --------------------------------------------- | ---------------------------------------------- |
| 7.1 | Teste de ambiente completo (compose up) | Validar execução unificada                    | Execução sem falhas e logs limpos              |
| 7.2 | Rodar ingestão completa (100% corpus)   | Popular bancos e índices                      | Relatório final de ingestão com totais e tempo |
| 7.3 | Rodar avaliação de desempenho (QA)      | Confirmar meta de precisão                    | Relatório “Avaliação Jurídica e Técnica”       |
| 7.4 | Publicar documentação                   | Tornar o Atlas MVP replicável                 | Pasta `/docs` versionada e organizada          |
| 7.5 | Encerrar Sprint 1                       | Revisão final e preparação p/ roadmap 60 dias | Reunião de encerramento + ata + roadmap 2.0    |
