# Relatório de Teste e Diagnóstico - RAG v1

**Data:** 2025-10-13

## 1. Objetivo do Teste

Validar a capacidade do pipeline RAG (Recuperação-Geração Aumentada) em responder a uma pergunta complexa que envolve a hierarquia de competências legislativas no sistema jurídico brasileiro.

## 2. Cenário de Teste

-   **Pergunta:** `"Uma lei municipal pode proibir a pesca em rios que atravessam o município?"`
-   **Comando Executado:** `python3 src/retriever/main.py --query "..." --generate`
-   **Hipótese Esperada:** O sistema deveria recuperar o Art. 24, inciso VI, da Constituição Federal, que trata da competência concorrente para legislar sobre pesca, e gerar uma resposta indicando que o município não pode legislar sobre o tema de forma isolada.

## 3. Resultados

### 3.1. Resposta Gerada

O sistema falhou em encontrar o contexto relevante e retornou a resposta padrão:

```
Com base nos documentos fornecidos, não foi possível encontrar uma resposta direta.
```

### 3.2. Documentos Recuperados (Contexto)

A análise dos documentos que a camada de recuperação selecionou revela a causa da falha. Os 5 principais documentos recuperados foram:

1.  **`br;go;constituicao;1989-10-05`, `art-7/inc-4`**: Trata de rios que banham mais de um município como bens do Estado.
2.  **`br;go;aparecida.goiania;lei.organica;2008-12-16;2008`, `art-222/par-1`**: Revoga leis sobre transporte coletivo.
3.  **`br;go;aparecida.goiania;lei.organica;2008-12-16;2008`, `art-125`**: Menciona a faculdade do Município de fazer algo, com autorização legislativa.
4.  **`br;go;constituicao;1989-10-05`, `art-88`**: Descreve o Plano Diretor.
5.  **`br;go;aparecida.goiania;lei.organica;2008-12-16;2008`, `art-23/par-1`**: Trata da retomada de serviços concedidos pelo Município.

## 4. Diagnóstico

A camada de recuperação falhou completamente. O sistema se concentrou em palavras-chave superficiais como "município" e "rios", mas não conseguiu capturar a intenção semântica da pergunta, que era sobre **competência para legislar**.

A causa raiz do problema reside na **baixa qualidade dos embeddings para o domínio jurídico**. O modelo de embedding pré-treinado que estamos utilizando (`distiluse-base-multilingual-cased-v1`) é um modelo de propósito geral. Ele não foi treinado para entender as nuances e as relações complexas do vocabulário jurídico, como a diferença entre competência concorrente, exclusiva e suplementar.

Como resultado, a busca vetorial não conseguiu identificar o Art. 24 da Constituição Federal como relevante, e a busca lexical, por si só, não foi suficiente.

## 5. Próximos Passos (Plano de Ação)

Para resolver essa deficiência, é imperativo melhorar a qualidade dos embeddings. A próxima etapa do projeto será a **Tarefa 5.3 - Fine-tuning do modelo de embedding**:

1.  **Criação de Dataset:** Gerar um dataset sintético de pares `(pergunta, dispositivo_relevante)` que cubra diversos aspectos do direito.
2.  **Fine-tuning:** Re-treinar o modelo de embedding `distiluse-base-multilingual-cased-v1` com este novo dataset para especializá-lo no domínio jurídico.
3.  **Re-embedding:** Após o fine-tuning, será necessário re-calcular os embeddings de todos os dispositivos no banco de dados com o novo modelo aprimorado.

A conclusão bem-sucedida desta etapa é crítica para a viabilidade e a precisão de todo o sistema RAG.