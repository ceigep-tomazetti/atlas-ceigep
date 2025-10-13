# 🧩 PLANO DE TAREFAS – ATLAS MVP

**Versão:** 1.0
**Horizonte:** 30 dias (Sprint 1)
**Base:** PRD do Atlas (LexML-first com grafo e RAG)
**Metodologia:** 5 blocos macro (Planejamento, Estrutura, Ingestão, Grafo, Avaliação)

---

## 🧱 BLOCO 1 – PLANEJAMENTO E FUNDAMENTAÇÃO

| Nº  | Tarefa                                        | Objetivo                                                              | Entregável de Conclusão                                                            |
| --- | --------------------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 1.1 | Definir equipe e papéis                       | Garantir que cada etapa tenha responsável técnico e jurídico          | Documento de papéis (ex: ingestão – dev; revisão – jurídico)                       |
| 1.2 | Confirmar escopo legal (CF, CE-GO, Aparecida) | Fixar corpus e limites do MVP                                         | Lista validada de atos (IDs, títulos, URLs oficiais)                               |
| 1.3 | Mapear fontes oficiais e formatos             | Identificar URLs, formatos (PDF/HTML/XML) e frequência de atualização | **Catálogo de Fontes** (planilha com 100% dos links e datas de última atualização) |
| 1.4 | Definir ambiente técnico                      | Padronizar stack Docker, portas, volumes e redes                      | Arquivo `docker-compose.yml` validado e documentado                                |
| 1.5 | Validar padrão LexML                          | Revisar estrutura XML e schema de referência                          | **Guia interno LexML Atlas**, resumindo tags e campos obrigatórios                 |

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
| 3.1 | **Coleta de dados oficiais**                   | Baixar e armazenar as fontes oficiais (CF, CE-GO, Aparecida) | Pasta MinIO `/br/...` com 100% dos arquivos + log de coleta |
| 3.2 | Criar **parser LexML**                         | Converter PDF/HTML/XML em JSON canônico LexML                | 10 amostras parseadas e validadas                           |
| 3.3 | Validar parser com LexML oficial (CF/CE-GO)    | Testar consistência estrutural e tags                        | Checklist 100% OK em 20 atos                                |
| 3.4 | Implementar **normalizador**                   | Limpar, corrigir e segmentar texto por dispositivos          | 100 leis normalizadas + relatório de offsets                |
| 3.5 | Criar **pipeline de carga (ETL)**              | Inserir JSON no Postgres e Neo4j com logs                    | Execução única com logs e contadores de sucesso/falha       |
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

## 🧮 BLOCO 6 – GOVERNANÇA, MONITORAMENTO E DOCUMENTAÇÃO

| Nº  | Tarefa                                     | Objetivo                                            | Entregável de Conclusão                            |
| --- | ------------------------------------------ | --------------------------------------------------- | -------------------------------------------------- |
| 6.1 | Configurar **monitoramento Docker**        | Garantir métricas de uptime e logs                  | Painel Grafana + Prometheus com 3 métricas básicas |
| 6.2 | Implementar **trilha de auditoria**        | Rastrear origem e alterações                        | Log estruturado JSON (ato, hash, vigência, origem) |
| 6.3 | Criar **painel de ingestão**               | Acompanhar número de atos e relações                | Dashboard simples com contadores                   |
| 6.4 | Documentar **estrutura de banco**          | Facilitar manutenção e expansão                     | Manual técnico (Postgres + Neo4j + MinIO)          |
| 6.5 | Criar **manual de ingestão e atualização** | Padronizar fluxos futuros                           | Documento “Procedimento de Atualização”            |
| 6.6 | Validar conformidade LexML                 | Checar URNs, estrutura e campos obrigatórios        | Relatório “Conformidade LexML – 100% aprovado”     |
| 6.7 | Produzir **documentação final**            | Consolidar tudo (dados, API, dicionário, grafo, QA) | Dossiê do MVP em PDF e Markdown                    |

---

## 🚀 BLOCO 7 – ENTREGA E TRANSIÇÃO

| Nº  | Tarefa                                  | Objetivo                                      | Entregável de Conclusão                        |
| --- | --------------------------------------- | --------------------------------------------- | ---------------------------------------------- |
| 7.1 | Teste de ambiente completo (compose up) | Validar execução unificada                    | Execução sem falhas e logs limpos              |
| 7.2 | Rodar ingestão completa (100% corpus)   | Popular bancos e índices                      | Relatório final de ingestão com totais e tempo |
| 7.3 | Rodar avaliação de desempenho (QA)      | Confirmar meta de precisão                    | Relatório “Avaliação Jurídica e Técnica”       |
| 7.4 | Publicar documentação                   | Tornar o Atlas MVP replicável                 | Pasta `/docs` versionada e organizada          |
| 7.5 | Encerrar Sprint 1                       | Revisão final e preparação p/ roadmap 60 dias | Reunião de encerramento + ata + roadmap 2.0    |

---

## 📅 LINHA DO TEMPO RESUMIDA

| Semana   | Blocos / Foco            | Principais Entregáveis                             |
| :------- | :----------------------- | :------------------------------------------------- |
| Semana 1 | Planejamento + Estrutura | Catálogo de Fontes, Dicionário de Dados, Ontologia |
| Semana 2 | Ingestão e Normalização  | Pipeline ETL + Corpus inicial + Logs               |
| Semana 3 | Grafo e Relações         | Grafo carregado + API de Relações                  |
| Semana 4 | RAG + QA + Documentação  | Motor de resposta + Avaliação + Dossiê final       |

---

## 🧾 CRITÉRIO GERAL DE ACEITE

Uma tarefa é considerada **concluída** quando:

1. O **objetivo declarado** está comprovadamente atendido;
2. O **entregável** existe em formato revisado (documento, script, dataset ou painel);
3. O resultado é **reprodutível** em ambiente Docker;
4. Há **registro de auditoria** ou log que confirme execução sem erro crítico.
