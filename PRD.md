# 🧭 PRD – Atlas MVP (LexML-First com Grafo)

### Versão: 1.0

### Data: 12 de outubro de 2025

### Responsável: CEIGEP / Atlas Project Team

### Escopo: Constituição Federal, Constituição do Estado de Goiás, legislação municipal de Aparecida de Goiânia

---

## 1. Visão Geral

O **Atlas** é uma plataforma de gestão e consulta da legislação pública estruturada segundo o **padrão LexML** e baseada em uma arquitetura **orientada a grafos e contexto temporal**.
O MVP será focado em um **ecossistema reduzido, porém completo**, cobrindo:

* Constituição Federal (CF/1988);
* Constituição do Estado de Goiás (CE-GO);
* Lei Orgânica e legislação selecionada de Aparecida de Goiânia.

A meta é oferecer um sistema **end-to-end**, desde a ingestão dos textos legais até a geração de respostas contextuais com citações precisas, relacionamentos entre normas e trilha de auditoria completa.

---

## 2. Objetivos

| Código | Objetivo                                                | Métrica de Sucesso                                                       |
| :----- | :------------------------------------------------------ | :----------------------------------------------------------------------- |
| O1     | Estruturar a base legal em formato compatível com LexML | 100% dos atos com URN válida e metadados LexML                           |
| O2     | Implementar grafo jurídico funcional                    | ≥ 90% das relações “altera / revoga / regulamenta” mapeadas corretamente |
| O3     | Oferecer respostas com pinpoint (ato + artigo + URN)    | 100% das respostas trazem dispositivo e fonte                            |
| O4     | Garantir precisão e verificabilidade                    | ≥ 85% de precisão nas respostas em conjunto de teste                     |
| O5     | Prover pipeline automatizado e reexecutável via Docker  | Ingestão completa em < 30 min em ambiente local                          |
| O6     | Implementar governança de dados                         | Todas as versões com hash e trilha de auditoria                          |

---

## 3. Escopo do MVP

### 3.1. Conteúdo

* **Federal:** Constituição Federal de 1988 (texto consolidado oficial).
* **Estadual:** Constituição do Estado de Goiás.
* **Municipal:** Lei Orgânica e ~150 leis ordinárias e complementares de Aparecida de Goiânia (seleção de alta relevância funcional).

### 3.2. Funcionalidades Incluídas

* Ingestão automática de textos (crawler ou upload manual).
* Parser e normalização LexML (XML → JSON canônico).
* Construção de grafo normativo (Neo4j) e base transacional (PostgreSQL).
* Indexação híbrida (BM25 + embeddings por dispositivo).
* API interna (REST/GraphQL) para consultas estruturadas.
* Mecanismo de RAG (recuperação e geração de respostas com citações).
* Painel de auditoria e logs de ingestão.

### 3.3. Funcionalidades Excluídas

* Edição de normas ou versionamento colaborativo.
* Interface pública externa (site ou portal).
* Multimunicípios (apenas Aparecida de Goiânia neste MVP).
* Consolidação automática de texto compilado completo (fase 2).

---

## 4. Estrutura Conceitual (Modelo LexML + Grafo)

### 4.1. Entidades Principais

| Entidade                | Descrição                                                           | Campos-Chave                                                                                                                                                  |
| :---------------------- | :------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **AtoNormativo**        | Representa o ato jurídico integral (Lei, Constituição, Emenda etc.) | `urn_lexml`, `tipo_ato`, `titulo`, `ementa`, `entidade_federativa`, `orgao_publicador`, `data_publicacao`, `fonte_oficial`, `hash_fonte`, `situacao_vigencia` |
| **Dispositivo**         | Unidade textual (artigo, parágrafo, inciso, alínea, item)           | `rotulo`, `ordem`, `texto`, `ancoras`, `caminho_estrutural`, `tipo_dispositivo`                                                                               |
| **VersaoTextual**       | Estado temporal de um dispositivo                                   | `vigencia_inicio`, `vigencia_fim`, `texto_normalizado`, `hash_texto`, `origem_alteracao`, `status_vigencia`                                                   |
| **EntidadePublicadora** | Órgão ou poder responsável                                          | `nome`, `sigla`, `esfera`, `competencia`                                                                                                                      |
| **FonteDocumento**      | Origem oficial do arquivo                                           | `url`, `formato`, `data_coleta`, `assinatura_digital`, `hash_bruto`                                                                                           |

### 4.2. Arestas do Grafo

| Relação           | Descrição                                      | Propriedades                              |
| :---------------- | :--------------------------------------------- | :---------------------------------------- |
| **ALTERA**        | Um ato altera outro (total ou parcial)         | `escopo`, `pinpoint`, `data_alteracao`    |
| **REVOGA**        | Um ato revoga outro (total ou parcial)         | `escopo`, `pinpoint`, `data_revogacao`    |
| **REGULAMENTA**   | Um ato regulamenta outro (geralmente superior) | `pinpoint`, `referencia_expressa`         |
| **CONSOLIDA**     | Ato que compila ou substitui anteriores        | `lista_substituidos`, `data_consolidacao` |
| **REMETE_A**      | Dispositivo faz remissão explícita a outro     | `expressao_citada`, `confianca_extracao`  |
| **CONTEM**        | Ato contém Dispositivo                         | -                                         |
| **POSSUI_VERSAO** | Dispositivo tem versões textuais               | -                                         |

---

## 5. Padrões e Vocabulários (PT-BR)

**Tipos de Ato:** constituição, emenda constitucional, lei complementar, lei ordinária, decreto, decreto legislativo, resolução, lei orgânica.
**Situação de Vigência:** vigente, revogado_total, revogado_parcial, com_vigencia_diferida, sem_vigencia_definida.
**Tipo de Relação:** altera, revoga, regulamenta, consolida, remete_a, cita, revalida, suspende_eficacia.
**Campos obrigatórios:** `urn_lexml`, `ementa`, `tipo_ato`, `fonte_oficial`, `vigencia_inicio`, `situacao_vigencia`.

---

## 6. Arquitetura Técnica (Dockerized)

### 6.1. Serviços Principais

| Serviço           | Tecnologia                          | Função                                           |
| :---------------- | :---------------------------------- | :----------------------------------------------- |
| **PostgreSQL**    | Banco relacional + JSONB + pgvector | Armazenamento transacional e busca vetorial      |
| **Neo4j**         | Grafo principal                     | Relações normativas e consultas estruturais      |
| **MinIO**         | Armazenamento de fontes             | PDFs/HTMLs/XMLs originais e versões normalizadas |
| **API Gateway**   | FastAPI / Node / Flask              | Camada de acesso e consulta                      |
| **Worker ETL**    | Python                              | Ingestão, parsing, normalização e carga          |
| **Scheduler**     | Cron / Airflow                      | Agendamento de coletas e atualizações            |
| **Monitoramento** | Grafana + Prometheus                | Logs, métricas e auditoria                       |

### 6.2. Fluxo de Dados

1. **Coleta:** download e registro da fonte (URL, data, hash).
2. **Parser:** extração de epígrafe, ementa, articulação, dispositivos.
3. **Normalização:** JSON compatível com LexML (atributos e estrutura).
4. **Carga:** inserção em PostgreSQL e Neo4j; salvamento no MinIO.
5. **Relações:** identificação e mapeamento das arestas (ALTERA, REVOGA etc.).
6. **Indexação:** embeddings por dispositivo + índice textual BM25.
7. **Consulta:** pipeline híbrido (BM25 + denso + rerank) → grafo → resposta.
8. **Auditoria:** log de resposta (URN, versão, hash, fonte, confiança).

---

## 7. Recuperação e Geração (RAG)

### 7.1. Estratégia

* **Recuperação híbrida:**

  * BM25 → ementa, palavras-chave, título.
  * Embeddings → corpo textual de dispositivos.
* **Filtro por jurisdição e vigência.**
* **Reranking** baseado em distância semântica e relevância hierárquica (priorizar CF > CE > municipal).
* **Contexto para o modelo:** 3–5 dispositivos mais relevantes + metadados (URN, vigência, órgão).
* **Resposta final:** texto explicativo + citações formatadas.

### 7.2. Política de “não sei”

Se confiança < limiar (0,6) ou conflito de versões, retornar:

> “O sistema identificou divergências ou ausência de norma vigente correspondente. Consulte os atos listados abaixo para confirmação.”

Com lista dos atos candidatos (URN + data + status).

---

## 8. Pipeline de Ingestão (End-to-End)

| Etapa           | Entrada       | Saída                         | Verificações                               |
| :-------------- | :------------ | :---------------------------- | :----------------------------------------- |
| 1. Coleta       | URLs oficiais | Arquivos brutos no MinIO      | Hash e metadados                           |
| 2. Parser       | PDF/HTML/XML  | JSON canônico LexML           | Estrutura hierárquica válida               |
| 3. Normalização | JSON          | Texto limpo + offsets         | Remoção de ruído e preservação de citações |
| 4. Carga DB     | JSON          | Registros em Postgres e Neo4j | Integridade e URN única                    |
| 5. Relações     | Texto         | Arestas ALTERA/REVOGA/etc     | Verificação de ambiguidade                 |
| 6. Indexação    | Dispositivos  | Embeddings + BM25             | Embeddings válidos e auditáveis            |
| 7. QA           | Corpus        | Métricas de precisão          | Checklist jurídico                         |

---

## 9. Avaliação e Qualidade

### 9.1. Conjunto de Teste

* 50 a 100 perguntas cobrindo:

  * Vigência de norma;
  * Relações entre atos;
  * Hierarquia CF/CE/municipal;
  * Base de competência e regulamentação.

### 9.2. Métricas

| Métrica                          | Descrição                       | Meta            |
| :------------------------------- | :------------------------------ | :-------------- |
| **Precisão Factual**             | Dispositivo correto e vigente   | ≥ 85%           |
| **Citação Correta**              | Ato + artigo + URN presentes    | 100%            |
| **Tempo de Resposta**            | Média de tempo por consulta     | ≤ 3 s           |
| **Cobertura de Relações**        | Relações válidas identificadas  | ≥ 90%           |
| **Taxa de “não sei” apropriada** | Respostas incertas justificadas | ≥ 95% adequadas |

### 9.3. Checklist de Resposta Jurídica

1. Dispositivo corresponde ao conteúdo da pergunta.
2. Vigência e data corretas.
3. Relações normativas indicadas.
4. Fonte oficial citada (URL + URN).
5. Hash e versão armazenados.

---

## 10. Governança e Atualização

* **Periodicidade:**

  * Federal e estadual: atualização mensal.
  * Municipal: atualização semanal (crawler portal + diário oficial).
* **Auditoria:**

  * Registro de toda modificação de texto, URN, fonte e hash.
  * Logs exportáveis em CSV/JSON.
* **Compliance:**

  * Dados públicos oficiais (sem LGPD).
  * Referência normativa: LexML Brasil ([https://lexml.gov.br](https://lexml.gov.br)).

---

## 11. Entregas do Sprint 1 (15 dias)

| Entrega | Descrição                                     | Critério de Aceite                       |
| :------ | :-------------------------------------------- | :--------------------------------------- |
| D1      | **Catálogo de Fontes** (CF, CE-GO, Aparecida) | URLs válidas e metadados completos       |
| D2      | **Dicionário de Dados e Vocabulário PT-BR**   | Compatível com LexML e JSON canônico     |
| D3      | **Esquema de Grafo (Neo4j)**                  | Nós e arestas implementáveis             |
| D4      | **Amostra de Corpus** (CF + CE-GO + 150 leis) | Ingerida e validada                      |
| D5      | **Plano de Extração de Relações**             | Padrões de detecção e regex documentados |
| D6      | **Conjunto de Avaliação (QA)**                | Perguntas + gabarito (URN + art.)        |
| D7      | **Ambiente Docker**                           | Todos serviços sob compose up sem erro   |
| D8      | **Relatório de QA**                           | ≥85% precisão factual em 50 consultas    |

---

## 12. Roadmap 30 / 60 / 90

| Período  | Meta                                     | Principais Entregas                               |
| :------- | :--------------------------------------- | :------------------------------------------------ |
| **D+30** | MVP operacional com grafo funcional      | Corpus carregado, API interna, 85% precisão       |
| **D+60** | Expansão municipal e painel de auditoria | 3 novos municípios, dashboard de ingestão         |
| **D+90** | API pública e consolidação automática    | Texto compilado, cache de respostas, multiusuário |

---

## 13. Regras de Nomeação (PT-BR)

* **AtoNormativo:** `ato_normativo`
* **Dispositivo:** `dispositivo`
* **VersaoTextual:** `versao_textual`
* **EntidadePublicadora:** `entidade_publicadora`
* **FonteDocumento:** `fonte_documento`
* **Relações:** `altera`, `revoga`, `regulamenta`, `consolida`, `remete_a`, `cita`

---

## 14. Riscos e Mitigações

| Risco                            | Impacto | Mitigação                                    |
| :------------------------------- | :------ | :------------------------------------------- |
| Falta de XML LexML oficial       | Médio   | Produzir JSON canônico espelhando o padrão   |
| Leis municipais não padronizadas | Alto    | Normalização manual e revisão de parser      |
| Ambiguidade em citações          | Médio   | Controle de confiança e marcação “incerto”   |
| Custos de hospedagem             | Baixo   | Containers locais via Docker Compose         |
| Baixa cobertura de relações      | Médio   | Regras linguísticas + revisão humana inicial |

---

## 15. Conclusão

O **Atlas MVP (LexML-First)** será o protótipo funcional de uma base jurídica municipal estruturada, com **padrão de dados nacional (LexML)**, **grafo normativo temporal** e **motor RAG** apto a responder perguntas com **referências precisas e verificáveis**.
Ele servirá de base para expansão a outros municípios e para a integração futura com sistemas da Câmara Municipal, portais legislativos e serviços de IA jurídica do CEIGEP.