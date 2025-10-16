# Diario de Bordo – Atlas (Reinicio)

- 2025-10-15 14:33 BRT — Instrucao permanente: toda decisao ou implementacao deve ser registrada neste diario (`docs/diario_de_bordo.md`).
- 2025-10-15 15:02 BRT — Planejando estrutura do catálogo de origens legislativas para nova implementação.
- 2025-10-15 16:08 BRT — Criadas migrações `20251015160541_000_create_source_origins` e `20251015160705_001_seed_fonte_origem_goias` definindo a tabela `fonte_origem` e cadastrando a API de dados abertos da Casa Civil de Goiás como primeira origem.
- 2025-10-15 16:20 BRT — Ajustando plano do crawler para fase de descoberta (registro de metadados sem download).
- 2025-10-15 16:32 BRT — Plano do crawler ajustado para usar fonte_origem.id como chave de estratégia e seguir convenções LexML de URN.
- 2025-10-15 16:40 BRT — Plano Crawler Fase 1 documentado: 
  * Objetivo: descobrir atos e registrar metadados/URLs sem baixar conteúdo, seguindo URNs LexML (padrão br;<esfera>;<jurisdição>;<tipo_ato>;<AAAA-MM-DD>;<número>). 
  * Modelagem: tabelas `fonte_documento` (fila de descobertas) e `fonte_origem_execucao` (histórico de execuções). 

- 2025-10-16 13:37 BRT — Ajustado parser determinístico para remover citações de artigos/parágrafos, separar anexos (`QUADRO/ANEXO/TABELA`) e limpar textos dos dispositivos; validamos contra a portaria `br;go;estadual;portaria.orçamentária;2025-08-27;182`, obtendo 100% de match com o JSON do LLM e atualizando o status da sugestão `6378dc59-1055-4411-bb36-caab7701e95b` para `implementada`.
  * Arquitetura: orquestrador em `src/crawler/main.py` que lê origens ativas (`fonte_origem.id` como chave), instancia estratégias `discover()` em `src/crawler/strategies/`, e realiza UPSERT na fila com payload bruto em JSON. 
  * Configuração: flags CLI (`--origin-id`, `--since`, `--until`, `--limit`, `--dry-run`) para controlar períodos; logs estruturados por origem; registros de execução com contagem de novos/duplicados/falhas. 
  * Próximos passos: migrar tabelas de fila, implementar esqueleto do crawler, codificar estratégia de descoberta para a API Casa Civil Goiás, validar execução piloto (ex: janeiro/2025).
- 2025-10-15 16:26 BRT — Migração 002 aplicada: tabelas 'fonte_documento' e 'fonte_origem_execucao' criadas.
- 2025-10-15 16:35 BRT — Implementada infraestrutura inicial do crawler: utilitário de banco (), modelos (), registro de estratégias, estratégia  e orquestrador ; criada lista de dependências .
- 2025-10-15 16:35 BRT — Implementada infraestrutura inicial do crawler: utilitário de banco (`src/utils/db.py`), modelos (`src/crawler/types.py`), registro de estratégias, estratégia GoiasApiDiscovery e orquestrador (`src/crawler/main.py`); criado `requirements.txt`.
- 2025-10-15 16:55 BRT — Atualizada estratégia de descoberta para vincular diretamente o UUID da origem (`fd64e393-159f-4484-9ea4-e9437753791d`), removendo dependência de slugs e garantindo correspondência 1:1 entre `fonte_origem` e implementação.
- 2025-10-15 17:00 BRT — Estratégia renomeada para `src/crawler/strategies/fd64e393_159f_4484_9ea4_e9437753791d.py`, consolidando convenção de arquivos por UUID de `fonte_origem`.
- 2025-10-15 17:05 BRT — Crawler migrado para cliente oficial do Supabase (`supabase==2.4.6`): novo utilitário `src/utils/db.py` cria client REST, `src/crawler/main.py` passou a usar fetch/update/insert via API, `requirements.txt` atualizado para remover psycopg2.
- 2025-10-15 17:47 BRT — Dry-run do crawler executado com sucesso (5 atos listados para jan/2025, origem fd64e393-159f-4484-9ea4-e9437753791d).
- 2025-10-15 17:50 BRT — Crawler executado (origem fd64e393-159f-4484-9ea4-e9437753791d, jan/2025, limite 5): 5 registros novos inseridos em fonte_documento e execução registrada em fonte_origem_execucao.
- 2025-10-15 18:05 BRT — Ajustes na estratégia de Goiás: datas convertidas para ISO e `metadados_brutos` armazenado em JSON nativo (sem stringificação) garantindo persistência consistente em `fonte_documento`.
- 2025-10-15 18:18 BRT — Adicionado modo `--backfill` ao crawler: itera mês a mês em ordem decrescente até interrupção manual, registrando execuções com observação `backfill`.
- 2025-10-15 18:25 BRT — Planejado pipeline completo do crawler (descoberta → extração) com armazenamento de texto bruto em `textos_brutos`/Supabase, ajuste do PRD e revisão de `data_publicacao_diario`. Próximo passo: atualizar PRD, corrigir parsing da data e implementar modos `--extract` e fluxo padrão discovery+extract.
- 2025-10-15 18:35 BRT — Preparando etapa de extração: adicionar colunas na tabela `fonte_documento`, criar modo `--extract` (com `--limit`) e fluxo padrão discovery→extract; validação da data de publicação confirmada.
- 2025-10-15 18:37 BRT — Migração 003 aplicada: adicionadas colunas `caminho_texto_bruto`, `hash_texto_bruto`, `texto_extraido_em` em `fonte_documento` para rastrear a extração.
- 2025-10-15 18:45 BRT — Implementados `--extract`, `--discover-only` e pipeline padrão discovery→extract; backfill agora aciona extração automaticamente. Estratégia de Goiás passa a produzir texto bruto sanitizado (`conteudo_sem_formatacao`) e salvar em `textos_brutos/`. Dependências de storage adicionadas (`src/utils/storage.py`).
- 2025-10-15 18:47 BRT — Correção no upload do storage: flag `upsert` agora enviada como string e caminho relativo calculado para `textos_brutos/`. Próximo passo: rerodar `--extract` para validar gravação no bucket.
- 2025-10-15 18:50 BRT — Ajuste de path no storage: sanitização ASCII (slugify) aplicada aos componentes da URN para evitar erros `InvalidKey` no Upload.
- 2025-10-15 18:55 BRT — Iniciando planejamento do parser determinístico a partir dos textos brutos (bucket 'textos_brutos').
- 2025-10-15 19:02 BRT — Parser determinístico aprovado: tratamento específico fica na etapa de extração (crawler) e o parser consome sempre `.txt` do bucket; JSON resultante será salvo em novo bucket dedicado e acompanhado por campos de status no banco. Preparando PRD/migração conforme diretrizes.
- 2025-10-15 19:05 BRT — Migração 004 aplicada: adicionados status (`status_parsing`, `status_normalizacao`) e colunas (`caminho_parser_json`, hashes, timestamps) na tabela `fonte_documento` para rastrear parser e normalização.
- 2025-10-15 19:12 BRT — Implementado parser determinístico: novo módulo `src/parser` lê textos do bucket `textos_brutos/`, gera JSON inicial via estratégia por origem (Goiás) e publica em `textos_estruturados/`, atualizando `status_parsing`. Utilitários de storage/db expandidos para download/upload de JSON.
- 2025-10-15 19:15 BRT — Dry-run do parser executado para 20 atos: textos carregados de  e JSONs gerados com hashes registrados (sem persistência).
- 2025-10-15 19:15 BRT — Dry-run do parser executado para 20 atos da origem Goiás: leitura do bucket `textos_brutos` e geração de JSON estruturado (hashes registrados, sem persistência).
- 2025-10-15 19:20 BRT — Preparando aprimoramento do parser: segmentar o texto único em dispositivos (Art., parágrafos, incisos) usando regex e fallback heurístico.
- 2025-10-15 19:28 BRT — Parser agora genérico: removidas estratégias específicas, criado módulo determinístico com segmentação de Art./§/incisos/alíneas e logging detalhado dos dispositivos no CLI.
- 2025-10-15 19:31 BRT — CLI do parser agora exibe resumo dos dispositivos no terminal quando em modo --dry-run, facilitando depuração.
- 2025-10-16 10:05 BRT — Definido fluxo híbrido: parser determinístico roda padrão; amostras passam por revisão Gemini (modo "review") para medir divergências, coletar sugestões regex e bloquear ingestões abaixo de 100% de aderência.
- 2025-10-15 19:40 BRT — Identificadas duas necessidades: (1) quando um artigo altera outros dispositivos, manter seus rótulos originais (ex.: ‘Art. 3º …’) sem tratar como artigos sequenciais; (2) separar anexos do corpo principal e armazená-los em coleção própria.
- 2025-10-15 19:50 BRT — Estratégia acordada: executar parser determinístico e parser assistido por LLM (Gemini) em paralelo, comparar outputs para evolução das heurísticas, e gradualmente reduzir o uso do LLM para amostragem/validação.
- 2025-10-15 19:58 BRT — Iniciando integração do parser assistido por LLM (Gemini): armazenar JSON paralelo, comparar com saída determinística e registrar divergências.
- 2025-10-15 20:05 BRT — Parser agora suporta modos `--mode=deterministic|llm|both`: integra Geminine (`src/utils/llm.py`), compara saídas e salva JSON único em `textos_estruturados/`. Dependências atualizadas.
- 2025-10-16 11:05 BRT — Planejadas melhorias no parser determinístico: tratar blocos de alteração (“passa a vigorar...”) como filhos com `tipo=alteracao`, reconhecer seções/subseções/capítulos como dispositivos, ampliar regex (`Art. 51-A`, `Parágrafo único`) e separar o fecho (cidade/data/assinaturas) de forma genérica.
- 2025-10-16 11:40 BRT — Implementadas heurísticas revisadas em `src/parser/deterministic.py`: novos padrões LexML, extração recursiva de blocos `“...” (NR)`, isolamento de fecho em `disposicao_final` e atribuição de ordens preservando preâmbulo; describe_heuristics atualizado para refletir o conjunto.
- 2025-10-16 11:45 BRT — PRD atualizado na seção de pipeline para registrar a tabela `llm_parser_sugestao`, garantindo rastreabilidade das recomendações de melhoria enviadas pelo Gemini.
- 2025-10-16 12:05 BRT — CLI do parser (`src/parser/main.py`) passou a suportar amostragem no modo `review` via `--review-sample-ratio` (com seed opcional), permitindo definir a proporção de itens revisados pelo Gemini em execuções de backfill; PRD ajustado para refletir a estratégia.
