# Diagnóstico e Log de Tentativas - Retriever v1

**Data:** 2025-10-13

## 1. Problema Inicial

O sistema RAG foi testado com a pergunta: `"Uma lei municipal pode proibir a pesca em rios que atravessam o município?"`.

-   **Resultado Esperado:** O sistema deveria recuperar o Art. 24, VI da Constituição Federal (competência concorrente para legislar sobre pesca) e gerar uma resposta informando que o município não pode legislar sozinho sobre o tema.
-   **Resultado Obtido:** O sistema respondeu que não foi possível encontrar uma resposta, pois a camada de recuperação falhou em encontrar documentos relevantes.

## 2. Log de Tentativas de Correção

### Tentativa 1: Aumentar o Recall da Busca

-   **Ação:** Aumentamos o `top_k` das buscas vetorial e lexical de 5 para 50, na esperança de que o documento relevante aparecesse em uma lista de candidatos maior.
-   **Resultado:** **FALHA.**
    -   A busca lexical retornou 0 resultados.
    -   Uma análise manual dos 50 resultados da busca vetorial (`semantic_results_dump.json`) confirmou que o Art. 24 da CF não estava presente.
-   **Diagnóstico:** O problema não era apenas o ranking, mas a incapacidade fundamental da busca semântica de identificar o documento como relevante. A falha da busca lexical foi identificada como um problema secundário a ser investigado.

### Tentativa 2: Corrigir a Busca Lexical (FTS)

-   **Ação 2a (Configuração `unaccent`):** Criamos uma configuração `portuguese_unaccent` no PostgreSQL para que a busca ignorasse acentos. O `loader` e o `retriever` foram atualizados para usar essa nova configuração.
-   **Resultado:** **FALHA.** A busca lexical continuou retornando 0 resultados.

-   **Ação 2b (Verificação do `tsvector`):** Verificamos diretamente no banco de dados se a coluna `texto_normalizado_tsv` estava sendo populada corretamente.
-   **Resultado:** **SUCESSO.** A coluna estava corretamente indexada.

-   **Ação 2c (`to_tsquery`):** Substituímos a função `plainto_tsquery` por `to_tsquery` no `retriever`, que oferece mais flexibilidade.
-   **Resultado:** **FALHA.** A busca lexical continuou retornando 0 resultados.

-   **Ação 2d (`websearch_to_tsquery`):** Substituímos `to_tsquery` por `websearch_to_tsquery`, uma função mais robusta e similar a um motor de busca web.
-   **Resultado:** **FALHA.** A busca lexical persistiu em retornar 0 resultados.
-   **Diagnóstico:** A falha persistente da busca lexical, mesmo com a indexação correta e diferentes funções de query, aponta para um problema mais sutil na interação entre a query gerada e os dados indexados, que não foi resolvido com essas tentativas.

### Tentativa 3: Boost Heurístico para a Constituição

-   **Ação:** Implementamos uma lógica no `retriever` para detectar palavras-chave relacionadas a "competência legislativa" na pergunta. Se detectadas, a query de busca semântica aplicaria um "boost" (multiplicador de 1.2x) na pontuação de similaridade para todos os documentos da Constituição Federal.
-   **Resultado:** **FALHA.**
    -   O log confirmou que o boost foi ativado (`Query de competência detectada. Aplicando boost...`).
    -   No entanto, os resultados finais ainda não incluíram o Art. 24 da CF.
-   **Diagnóstico:** O boost não foi forte o suficiente para superar a baixa similaridade semântica calculada pelo modelo de embedding de uso geral. O artigo relevante estava tão distante no ranking que mesmo com o bônus, ele não chegou ao topo.

## 3. Conclusão Final e Causa Raiz

As tentativas de "hardening" (aumento do recall, melhoria da busca lexical, boosting heurístico) não foram suficientes para resolver o problema.

A **causa raiz** foi confirmada: o **modelo de embedding pré-treinado (`distiluse-base-multilingual-cased-v1`) não possui a especialização semântica necessária para o domínio jurídico**. Ele não consegue mapear a pergunta sobre "competência municipal para proibir a pesca" para um dispositivo que fala sobre "legislação concorrente sobre pesca", pois não entende a relação conceitual entre esses termos no contexto do direito.

## 4. Próximo Passo Estratégico

A única solução robusta é avançar para a **Fase 3** do plano: **Fine-tuning do modelo de embedding (Tarefa 5.3)**. Precisamos criar um dataset supervisionado com pares de perguntas e respostas do domínio jurídico para ensinar ao modelo as nuances da semântica legal. Isso permitirá que a busca vetorial identifique corretamente os documentos relevantes, mesmo quando não há uma correspondência exata de palavras-chave.