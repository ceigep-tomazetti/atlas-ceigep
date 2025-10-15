# Repository Guidelines

## Fontes de Verdade e Organização
Consulte sempre `docs/PRD.md` (versão 1.0) e `docs/tarefas.md` (versão 1.1); esses documentos descrevem o MVP LexML-first, o corpus federal/estadual/municipal e o plano em blocos. Estruture o trabalho seguindo o pipeline descrito no PRD: `crawler` descobre e coleta fontes oficiais, `run_pipeline.py` orquestra a fila, `parser` e `preprocessor` geram o JSON hierárquico via LLM, `normalizer` garante conformidade LexML, `loader` grava em Supabase/Neo4j e os módulos `linker` e `temporal_validator` enriquecem o grafo.

## Fluxos Operacionais
1. Mantenha a fila `fonte_documento` alinhada com o catálogo de fontes e a política de vigência definidos nos blocos 1 e 2.
2. Execute o pipeline com `python3 run_pipeline.py` após preparar manifestos ou coletas; monitore logs e atualize o status conforme a tabela do PRD (PENDENTE → COLETADO → PROCESSADO).
3. Valide ingestões amostrais conforme as metas dos blocos 3 e 4: 10 atos parseados, 100 leis normalizadas e grafo com relações `ALTERA/REVOGA` ≥ 90% corretas.
4. Para recuperação e RAG, siga as diretrizes de indexação híbrida e resposta “não sei” descritas na Seção 7 do PRD.

## Estilo LexML e Conformidade
Todo código e dados devem preservar URNs válidas, metadados completos e hashes por versão (objetivo O6). As entidades do grafo precisam refletir a ontologia e o dicionário de dados planejados no Bloco 2. Sempre compare estruturas geradas com os documentos auxiliares citados no plano (ontologia, dicionário, política de versões) antes de aprovar mudanças.

## Testes e Critérios de Aceite
Cada entrega deve provar a métrica correspondente: validade LexML (O1), relações corretas (O2), respostas com pinpoint (O3) e precisão ≥ 85% (O4). Documente execuções do pipeline e dos testes de avaliação previstos no Bloco 5, incluindo logs de ingestão, relatórios de offsets e verificações contra Supabase/Neo4j.

## Commits e Revisões
Faça commits pequenas e alinhadas aos números de tarefa (`3.4`, `4.2`, etc.), referenciando a etapa do plano. Pull Requests precisam linkar o objetivo do PRD que estão endereçando e anexar evidências (logs, métricas ou checklists) exigidas como entregáveis em `docs/tarefas.md`.

## Segurança e Configuração
Respeite o ambiente descrito no Bloco 1: Docker Compose para serviços locais, Supabase para armazenamento e banco e política de `.env` fora do versionamento. Garanta trilha de auditoria completa em cada execução e, antes de mergear, confirme que o pipeline pode ser reexecutado em <30 minutos, conforme objetivo O5.
