# src/retriever/main.py
import os
from psycopg2.extras import RealDictCursor
from sentence_transformers import SentenceTransformer
import logging
import argparse
import json
import sys
from src.utils.db import get_db_connection

# --- Configuração ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MODEL_NAME = 'distiluse-base-multilingual-cased-v1'

# --- Lógica de Recuperação ---

def semantic_search(conn, query_text, query_embedding, top_k=10):
    """Executa a busca por similaridade de cosseno com boost constitucional."""
    logging.info("Executando busca semântica (vetorial)...")
    
    # Heurística para detectar perguntas sobre competência
    competence_keywords = ['pode o município', 'competência', 'legislar', 'proibir', 'regular']
    is_competence_query = any(keyword in query_text.lower() for keyword in competence_keywords)
    
    boost_clause = ""
    if is_competence_query:
        logging.info("Query de competência detectada. Aplicando boost para a Constituição Federal.")
        boost_clause = "CASE WHEN an.urn_lexml LIKE 'br;federal;constituicao;%' THEN 1.2 ELSE 1.0 END *"

    embedding_str = str(query_embedding.tolist())

    query = f"""
    SELECT 
        vt.id,
        vt.texto_normalizado,
        d.caminho_estrutural,
        an.urn_lexml,
        ({boost_clause} (1 - (embedding <=> '{embedding_str}'))) AS similarity
    FROM versao_textual vt
    JOIN dispositivo d ON vt.dispositivo_id = d.id
    JOIN ato_normativo an ON d.ato_id = an.id
    WHERE vt.embedding IS NOT NULL
    ORDER BY similarity DESC
    LIMIT {top_k};
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        return cur.fetchall()

def lexical_search(conn, query_text, top_k=10):
    """Executa a busca por texto completo (FTS) usando websearch_to_tsquery."""
    logging.info("Executando busca lexical (FTS)...")
    
    query = """
    SELECT 
        vt.id,
        vt.texto_normalizado,
        d.caminho_estrutural,
        an.urn_lexml,
        ts_rank(vt.texto_normalizado_tsv, phraseto_tsquery('public.portuguese_unaccent', %s)) AS rank
    FROM versao_textual vt
    JOIN dispositivo d ON vt.dispositivo_id = d.id
    JOIN ato_normativo an ON d.ato_id = an.id
    WHERE vt.texto_normalizado_tsv @@ phraseto_tsquery('public.portuguese_unaccent', %s)
    ORDER BY rank DESC
    LIMIT %s;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (query_text, query_text, top_k))
        return cur.fetchall()

def hybrid_fusion(semantic_results, lexical_results):
    """Combina e re-rankeia os resultados usando Reciprocal Rank Fusion (RRF)."""
    logging.info("Combinando resultados com Reciprocal Rank Fusion...")
    
    fused_scores = {}
    k = 60  # Constante de ranking, comum em RRF

    # Processa resultados semânticos
    for i, doc in enumerate(semantic_results):
        doc_id = doc['id']
        if doc_id not in fused_scores:
            fused_scores[doc_id] = {"score": 0, "doc": doc}
        fused_scores[doc_id]["score"] += 1 / (k + i + 1)

    # Processa resultados lexicais
    for i, doc in enumerate(lexical_results):
        doc_id = doc['id']
        if doc_id not in fused_scores:
            fused_scores[doc_id] = {"score": 0, "doc": doc}
        fused_scores[doc_id]["score"] += 1 / (k + i + 1)

    # Ordena os resultados pelo score RRF
    sorted_results = sorted(fused_scores.values(), key=lambda x: x["score"], reverse=True)
    
    # Retorna apenas os documentos ordenados
    return [item["doc"] for item in sorted_results]

def generate_answer(query, context_docs):
    """Simula a geração de uma resposta por um LLM a partir do contexto."""
    logging.info("Gerando resposta com base no contexto recuperado...")
    
    context = "\n\n---\n\n".join([doc['texto_normalizado'] for doc in context_docs])
    
    prompt = f"""
Você é um assistente jurídico especializado na legislação brasileira. Sua tarefa é responder à pergunta do usuário de forma clara e objetiva, baseando-se exclusivamente nos trechos da legislação fornecidos abaixo. Não utilize nenhum conhecimento prévio.

**Instruções:**
1.  Leia atentamente a pergunta do usuário.
2.  Analise os trechos da legislação fornecidos no contexto.
3.  Formule uma resposta direta para a pergunta, utilizando apenas as informações contidas nos textos.
4.  Se os textos não contiverem a resposta, afirme que "Com base nos documentos fornecidos, não foi possível encontrar uma resposta direta."
5.  Cite os artigos ou dispositivos legais que fundamentam sua resposta ao final, se aplicável.

**Contexto (Trechos da Legislação):**
{context}

**Pergunta do Usuário:**
{query}

**Resposta:**
"""
    
    # Em um cenário real, aqui seria a chamada para a API do LLM
    # Ex: response = gemini_model.generate_content(prompt)
    # Para este exemplo, vamos simular uma resposta direta baseada no prompt.
    # A "mágica" acontece aqui, onde o modelo (eu) gera a resposta.
    # O código abaixo é uma simulação simplificada.
    
    # Simulação de lógica para encontrar a resposta no contexto
    if "direitos dos trabalhadores" in query.lower() and any("Art. 7º" in doc['texto_normalizado'] for doc in context_docs):
        return """
Com base na legislação fornecida, os direitos dos trabalhadores urbanos e rurais, que visam a melhoria de sua condição social, incluem:

- **Proteção no Emprego:** Relação de emprego protegida contra despedida arbitrária ou sem justa causa, com previsão de indenização.
- **Seguro-Desemprego:** Garantia de seguro em caso de desemprego involuntário.
- **FGTS:** Direito ao Fundo de Garantia do Tempo de Serviço.
- **Salário:** Salário mínimo nacionalmente unificado, irredutibilidade salarial (salvo acordo), garantia de salário nunca inferior ao mínimo para remuneração variável, e décimo terceiro salário.
- **Jornada de Trabalho:** Duração do trabalho não superior a 8 horas diárias e 44 semanais, jornada de 6 horas para turnos ininterruptos, e repouso semanal remunerado.
- **Férias:** Gozo de férias anuais remuneradas com acréscimo de um terço do salário.
- **Licenças:** Licença à gestante de 120 dias e licença-paternidade.
- **Segurança e Saúde:** Redução dos riscos inerentes ao trabalho por meio de normas de saúde, higiene e segurança, e adicional para atividades penosas, insalubres ou perigosas.
- **Aposentadoria:** Direito à aposentadoria.
- **Proibição de Discriminação:** Proibição de diferença de salários e de critério de admissão por motivo de sexo, idade, cor, estado civil ou deficiência.

Fundamentação: Art. 7º da Constituição Federal.
"""
    else:
        return "Com base nos documentos fornecidos, não foi possível encontrar uma resposta direta."


# --- Função Principal ---
def main(query, top_k, generate):
    """Função principal para orquestrar a recuperação híbrida."""
    db_conn = get_db_connection()
    if not db_conn:
        sys.exit(1)

    try:
        # 1. Carregar modelo e gerar embedding da query
        logging.info(f"Carregando modelo '{MODEL_NAME}'...")
        model = SentenceTransformer(MODEL_NAME)
        query_embedding = model.encode(query)
        logging.info("Embedding da query gerado.")

        # 2. Executar as buscas com um recall maior
        initial_top_k = 50
        semantic_results = semantic_search(db_conn, query, query_embedding, initial_top_k)
        lexical_results = lexical_search(db_conn, query, initial_top_k)
        logging.info(f"Busca semântica retornou {len(semantic_results)} resultados.")
        logging.info(f"Busca lexical retornou {len(lexical_results)} resultados.")

        # 3. Combinar e re-rankear
        final_results = hybrid_fusion(semantic_results, lexical_results)

        # 4. Apresentar resultados
        if generate:
            answer = generate_answer(query, final_results[:top_k])
            print(answer)
        else:
            logging.info(f"Top {top_k} resultados combinados:")
            output_results = []
            for i, doc in enumerate(final_results[:top_k]):
                result = {
                    "rank": i + 1,
                    "urn": doc['urn_lexml'],
                    "caminho": doc['caminho_estrutural'],
                    "texto": doc['texto_normalizado'],
                    "similaridade_semantica": doc.get('similarity'),
                    "rank_lexical": doc.get('rank')
                }
                output_results.append(result)
            print(json.dumps(output_results, indent=2, ensure_ascii=False))

    finally:
        db_conn.close()
        logging.info("Conexão com o PostgreSQL fechada.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Camada de Recuperação Híbrida do Atlas.")
    parser.add_argument("--query", type=str, required=True, help="A pergunta ou termo de busca.")
    parser.add_argument("--top_k", type=int, default=5, help="O número de resultados a serem retornados.")
    parser.add_argument("--generate", action="store_true", help="Ativa a geração de resposta em linguagem natural.")
    args = parser.parse_args()
    
    main(args.query, args.top_k, args.generate)
