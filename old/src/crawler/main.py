# src/crawler/main.py
import os
import sys
import argparse
import logging
import json
from src.utils.db import get_db_connection

import hashlib
import importlib.util
from datetime import datetime
import requests
from src.utils.storage import get_storage_client, upload_file

# --- Configuração ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SPIDERS_DIR = os.path.join(os.path.dirname(__file__), 'spiders')

# --- Lógica do Orquestrador ---
def load_spiders():
    """Carrega dinamicamente todos os módulos de spider do diretório 'spiders'."""
    spiders = []
    for filename in os.listdir(SPIDERS_DIR):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]
            module_path = os.path.join(SPIDERS_DIR, filename)
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'collect'):
                spiders.append(module)
                logging.info(f"Spider '{module_name}' carregada.")
    return spiders

def run_spiders_and_populate(conn, source_name=None, limit=None):
    """Executa spiders, que 'yield' fontes, e as insere iterativamente no banco."""
    spiders_to_run = load_spiders()
    if source_name:
        spiders_to_run = [s for s in spiders_to_run if s.__name__ == source_name]
        if not spiders_to_run:
            logging.error(f"Spider '{source_name}' não encontrada.")
            return

    if not spiders_to_run:
        logging.warning("Nenhuma spider para executar.")
        return

    total_inserted = 0
    with conn.cursor() as cur:
        for spider in spiders_to_run:
            try:
                spider_inserted = 0
                # O spider.collect() agora é um gerador (yields)
                for i, source in enumerate(spider.collect()):
                    if limit and i >= limit:
                        logging.info(f"Limite de {limit} fontes atingido para a spider '{spider.__name__}'.")
                        break
                    
                    cur.execute(
                        """
                        INSERT INTO fonte_documento (urn_lexml, url_fonte, metadados_fonte, status)
                        VALUES (%s, %s, %s, 'PENDENTE')
                        ON CONFLICT (urn_lexml) DO NOTHING;
                        """,
                        (source['urn'], source['url_fonte'], json.dumps(source['metadados']))
                    )
                    if cur.rowcount > 0:
                        spider_inserted += 1
                
                conn.commit() # Commit no final de cada spider
                total_inserted += spider_inserted
                logging.info(f"Spider '{spider.__name__}' inseriu {spider_inserted} novas fontes.")
            except Exception as e:
                logging.error(f"Erro ao executar a spider '{spider.__name__}': {e}")
                conn.rollback()
    logging.info(f"População concluída. Total de {total_inserted} novas fontes inseridas.")

def process_pending_sources(conn, limit=None):
    """Busca fontes pendentes, baixa o conteúdo, faz upload para o Supabase Storage e atualiza o status."""
    storage_client = get_storage_client()
    if not storage_client:
        logging.error("Não foi possível inicializar o cliente de storage. Abortando.")
        return

    with conn.cursor() as cur:
        query = "SELECT id, urn_lexml, url_fonte FROM fonte_documento WHERE status = 'PENDENTE'"
        params = []
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cur.execute(query, params)
        pending_sources = cur.fetchall()
    
    logging.info(f"Encontradas {len(pending_sources)} fontes pendentes para processar.")
    processed_count = 0
    for source_id, urn, url in pending_sources:
        try:
            if not url:
                logging.warning(f"Fonte ignorada (URL vazia): {urn}")
                continue

            # Baixa o conteúdo do site de origem
            response = requests.get(url, headers={'User-Agent': "Mozilla/5.0"}, timeout=120, stream=True)
            response.raise_for_status()
            content = response.content
            file_hash = hashlib.sha256(content).hexdigest()

            # Define o caminho no bucket do Supabase
            file_extension = '.html' if 'planalto.gov.br' in url else '.pdf'
            destination_path = f"{urn.replace(';', '/')}{file_extension}"

            # Faz o upload para o Supabase Storage
            if not upload_file(storage_client, content, destination_path):
                raise Exception("Falha no upload para o Supabase Storage.")

            # Atualiza o banco de dados com o novo status e caminho do bucket
            with conn.cursor() as update_cur:
                update_cur.execute(
                    """
                    UPDATE fonte_documento
                    SET status = 'COLETADO', data_coleta = %s, hash_conteudo_bruto = %s, caminho_arquivo_local = %s, data_atualizacao = %s
                    WHERE id = %s;
                    """,
                    (datetime.utcnow(), file_hash, destination_path, datetime.utcnow(), source_id)
                )
            conn.commit()
            logging.info(f"Fonte processada e enviada para o Storage: {urn}")
            processed_count += 1

        except requests.RequestException as e:
            logging.error(f"Erro ao baixar {url} para {urn}: {e}")
            with conn.cursor() as err_cur:
                err_cur.execute("UPDATE fonte_documento SET status = 'FALHA' WHERE id = %s;", (source_id,))
            conn.commit()
        except Exception as e:
            logging.error(f"Erro inesperado ao processar {urn}: {e}")
            with conn.cursor() as err_cur:
                err_cur.execute("UPDATE fonte_documento SET status = 'FALHA' WHERE id = %s;", (source_id,))
            conn.commit()

    logging.info(f"Processamento concluído. {processed_count} fontes atualizadas para 'COLETADO'.")

# --- Função Principal ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orquestrador de crawlers e processador de fontes.")
    parser.add_argument("--populate", action="store_true", help="Executa spiders para popular a tabela de fontes.")
    parser.add_argument("--process", action="store_true", help="Processa (baixa) as fontes pendentes.")
    parser.add_argument("--limit", type=int, help="Limita o número de itens a serem coletados ou processados.")
    parser.add_argument("--source", type=str, help="Executa apenas uma spider específica (pelo nome do arquivo, ex: goias_api).")
    
    args = parser.parse_args()

    if not args.populate and not args.process:
        parser.error("Nenhuma ação especificada. Use --populate ou --process.")

    db_conn = get_db_connection()
    if not db_conn:
        sys.exit(1)

    try:
        if args.populate:
            run_spiders_and_populate(db_conn, args.source, args.limit)
        if args.process:
            process_pending_sources(db_conn, args.limit)
    finally:
        db_conn.close()
        logging.info("Conexão com o PostgreSQL fechada.")
