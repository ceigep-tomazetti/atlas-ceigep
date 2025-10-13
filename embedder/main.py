# embedder/main.py
import os
import psycopg2
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import logging
import time

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def connect_db():
    """Conecta ao banco de dados PostgreSQL."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host="localhost",
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        logging.info("Conexão com o PostgreSQL bem-sucedida.")
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Erro ao conectar ao PostgreSQL: {e}")
        return None

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

def generate_and_update_embeddings(conn, records, model):
    """Gera embeddings e atualiza o banco de dados."""
    if not records:
        logging.info("Nenhum dispositivo para processar.")
        return

    logging.info(f"Iniciando a geração de embeddings para {len(records)} dispositivos...")
    start_time = time.time()

    texts = [rec[1] for rec in records]
    ids = [rec[0] for rec in records]

    # Gera todos os embeddings de uma vez para otimização
    embeddings = model.encode(texts, show_progress_bar=True)

    with conn.cursor() as cur:
        for i, record_id in enumerate(ids):
            embedding_vector = embeddings[i].tolist()
            # A extensão pgvector espera um formato de string como '[1,2,3]'
            embedding_str = str(embedding_vector)

            update_query = "UPDATE versao_textual SET embedding = %s WHERE id = %s;"
            cur.execute(update_query, (embedding_str, record_id))

    conn.commit()
    end_time = time.time()
    logging.info(f"Embeddings gerados e salvos com sucesso para {len(records)} dispositivos.")
    logging.info(f"Tempo total: {end_time - start_time:.2f} segundos.")


def main():
    """Função principal para orquestrar a geração de embeddings."""
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

    conn = connect_db()
    if not conn:
        return

    try:
        # Carrega o modelo. Ele será baixado na primeira execução.
        logging.info("Carregando o modelo de sentence-transformer...")
        model_name = 'distiluse-base-multilingual-cased-v1'
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
