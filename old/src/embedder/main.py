# embedder/main.py
import os
from sentence_transformers import SentenceTransformer
import logging
import time
from src.utils.db import get_db_connection

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def fetch_devices_without_embedding(conn):
    """Busca dispositivos que ainda não possuem embedding."""
    query = """
    SELECT id, texto_normalizado
    FROM versao_textual
    WHERE embedding IS NULL;
    """
    with conn.cursor() as cur:
        cur.execute(query)
        records = cur.fetchall()
        logging.info(f"Encontrados {len(records)} dispositivos sem embedding.")
        return records

def generate_and_update_embeddings(conn, records, model, batch_size=500):
    """Gera embeddings e atualiza o banco de dados em lotes."""
    if not records:
        logging.info("Nenhum dispositivo para processar.")
        return

    logging.info(f"Iniciando a geração de embeddings para {len(records)} dispositivos em lotes de {batch_size}...")
    start_time = time.time()

    for i in range(0, len(records), batch_size):
        batch_records = records[i:i + batch_size]
        batch_texts = [rec[1] for rec in batch_records]
        batch_ids = [rec[0] for rec in batch_records]
        
        logging.info(f"Processando lote {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size}...")

        # Gera todos os embeddings do lote de uma vez
        embeddings = model.encode(batch_texts, show_progress_bar=True)

        with conn.cursor() as cur:
            for j, record_id in enumerate(batch_ids):
                embedding_vector = embeddings[j].tolist()
                embedding_str = str(embedding_vector)

                update_query = "UPDATE versao_textual SET embedding = %s WHERE id = %s;"
                cur.execute(update_query, (embedding_str, record_id))
        
        conn.commit()
        logging.info(f"Lote {i//batch_size + 1} concluído e salvo no banco.")

    end_time = time.time()
    logging.info(f"Embeddings gerados e salvos com sucesso para {len(records)} dispositivos.")
    logging.info(f"Tempo total: {end_time - start_time:.2f} segundos.")


def main():
    """Função principal para orquestrar a geração de embeddings."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        # Carrega o modelo. Ele será baixado na primeira execução.
        logging.info("Carregando o modelo de sentence-transformer...")
        model_name = 'stjiris/bert-large-portuguese-cased-legal-mlm-gpl-nli-sts-v1'
        model = SentenceTransformer(model_name)
        logging.info(f"Modelo '{model_name}' carregado com sucesso.")

        records_to_process = fetch_devices_without_embedding(conn)
        generate_and_update_embeddings(conn, records_to_process, model)

    finally:
        if conn:
            conn.close()
            logging.info("Conexão com o PostgreSQL fechada.")

if __name__ == "__main__":
    main()
