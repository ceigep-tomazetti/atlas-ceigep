# crawler/main.py
import requests
import os
import json
import argparse
import logging
import psycopg2
import sys
import hashlib
from datetime import datetime
from dotenv import load_dotenv

# --- Configuração ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

API_ENDPOINT = "https://legisla.casacivil.go.gov.br/api/v2/pesquisa/legislacoes/dados_abertos.json?tipo_legislacao=13"
DOWNLOAD_DIR = "tmp_analise"
USER_AGENT = "Mozilla/5.0 (compatible; AtlasProjectCrawler/1.0; +https://github.com/tomazetti/ceigep-atlas-data)"

# --- Funções de Banco de Dados ---
def connect_db_postgres():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"), user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"), host="localhost",
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        logging.info("Conexão com o PostgreSQL bem-sucedida.")
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Erro ao conectar ao PostgreSQL: {e}")
        return None

# --- Lógica do Crawler ---
def populate_sources_from_api(conn):
    """Busca na API de dados abertos e popula a tabela fonte_documento."""
    logging.info(f"Buscando dados da API: {API_ENDPOINT}")
    try:
        response = requests.get(API_ENDPOINT, headers={'User-Agent': USER_AGENT}, timeout=60)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logging.error(f"Erro ao buscar dados da API: {e}")
        return

    logging.info(f"Encontrados {len(data)} itens na API. Populando o banco de dados...")
    inserted_count = 0
    with conn.cursor() as cur:
        for item_str in data:
            try:
                item = json.loads(item_str)
                date_obj = datetime.strptime(item['data_legislacao'], '%d/%m/%Y')
                formatted_date = date_obj.strftime('%Y-%m-%d')
                # O slug para emenda constitucional é 'emenda.constitucional'
                urn = f"br;go;estadual;emenda.constitucional;{formatted_date};{item['numero']}"
                url_fonte = item['diarios'][0]['link_download']

                cur.execute(
                    """
                    INSERT INTO fonte_documento (urn_lexml, url_fonte, metadados_fonte, status)
                    VALUES (%s, %s, %s, 'PENDENTE')
                    ON CONFLICT (urn_lexml) DO NOTHING;
                    """,
                    (urn, url_fonte, json.dumps(item))
                )
                if cur.rowcount > 0:
                    inserted_count += 1
            except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
                logging.warning(f"Item inválido ou sem link de download ignorado: {e}")
        conn.commit()
    logging.info(f"População concluída. {inserted_count} novas fontes inseridas como 'PENDENTE'.")

def process_pending_sources(conn):
    """Busca fontes pendentes, baixa o conteúdo e atualiza o status."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    with conn.cursor() as cur:
        cur.execute("SELECT id, urn_lexml, url_fonte FROM fonte_documento WHERE status = 'PENDENTE'")
        pending_sources = cur.fetchall()
    
    logging.info(f"Encontradas {len(pending_sources)} fontes pendentes para processar.")
    processed_count = 0
    for source_id, urn, url in pending_sources:
        try:
            if not url:
                logging.warning(f"Fonte ignorada (URL vazia): {urn}")
                continue

            pdf_filename = f"ato_{urn.replace(';', '_')}.pdf"
            pdf_path = os.path.join(DOWNLOAD_DIR, pdf_filename)
            
            response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=120, stream=True)
            response.raise_for_status()
            
            content = response.content
            file_hash = hashlib.sha256(content).hexdigest()

            with open(pdf_path, 'wb') as f:
                f.write(content)
            
            with conn.cursor() as update_cur:
                update_cur.execute(
                    """
                    UPDATE fonte_documento
                    SET status = 'COLETADO', data_coleta = %s, hash_conteudo_bruto = %s, caminho_arquivo_local = %s, data_atualizacao = %s
                    WHERE id = %s;
                    """,
                    (datetime.utcnow(), file_hash, os.path.abspath(pdf_path), datetime.utcnow(), source_id)
                )
            conn.commit()
            logging.info(f"Fonte processada com sucesso: {urn}")
            processed_count += 1
        except requests.RequestException as e:
            logging.error(f"Erro ao baixar {url} para {urn}: {e}")
            with conn.cursor() as err_cur:
                err_cur.execute("UPDATE fonte_documento SET status = 'FALHA' WHERE id = %s;", (source_id,))
            conn.commit()
        except Exception as e:
            logging.error(f"Erro inesperado ao processar {urn}: {e}")

    logging.info(f"Processamento concluído. {processed_count} fontes atualizadas para 'COLETADO'.")

# --- Função Principal ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawler e processador de fontes para o Atlas.")
    parser.add_argument("--populate", action="store_true", help="Popula a tabela de fontes a partir da API.")
    parser.add_argument("--process", action="store_true", help="Processa (baixa) as fontes pendentes.")
    
    args = parser.parse_args()

    if not args.populate and not args.process:
        parser.error("Nenhuma ação especificada. Use --populate ou --process.")

    db_conn = connect_db_postgres()
    if not db_conn:
        sys.exit(1)

    try:
        if args.populate:
            populate_sources_from_api(db_conn)
        if args.process:
            process_pending_sources(db_conn)
    finally:
        db_conn.close()
        logging.info("Conexão com o PostgreSQL fechada.")