# run_pipeline.py
import os
import subprocess
import logging
import json
import sys
import argparse
from datetime import datetime
from src.utils.db import get_db_connection
from src.utils.storage import get_storage_client, download_file

# --- Configuração ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
TEMP_DOWNLOAD_DIR = "tmp_pipeline_files"

# --- Funções de Banco de Dados ---
def get_sources_to_process(conn, urn=None, limit=None):
    """Busca por fontes com status 'PENDENTE' ou 'FALHA', com filtros opcionais."""
    query = "SELECT id, urn_lexml, metadados_fonte, url_fonte FROM fonte_documento WHERE status IN ('PENDENTE', 'FALHA')"
    params = []
    if urn:
        query += " AND urn_lexml = %s"
        params.append(urn)
    
    query += " ORDER BY data_criacao ASC" # Processa as mais antigas primeiro
    
    if limit:
        query += " LIMIT %s"
        params.append(limit)
        
    with conn.cursor() as cur:
        cur.execute(query, tuple(params))
        return cur.fetchall()

def update_source_status(conn, source_id, status):
    """Atualiza o status de uma fonte no banco de dados."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE fonte_documento SET status = %s, data_atualizacao = %s WHERE id = %s",
            (status, datetime.utcnow(), source_id)
        )
    conn.commit()
    logging.info(f"Status da fonte {source_id} atualizado para '{status}'.")

def create_temp_manifest(urn, metadata, source_url):
    """Cria um arquivo de manifesto temporário para o pipeline."""
    manifest_data = {
        "urn_lexml": urn,
        "tipo_ato": metadata.get("tipo_legislacao"),
        "titulo": metadata.get("ementa"),
        "ementa": metadata.get("ementa"),
        "entidade_federativa": "Estadual",
        "orgao_publicador": metadata.get("autor", "Governo do Estado de Goiás"),
        "data_publicacao": metadata.get("data_legislacao"),
        "source_url": source_url,
        "metadados_fonte": metadata
    }
    
    temp_manifest_path = os.path.join(TEMP_DOWNLOAD_DIR, f"temp_manifest_{urn.replace(';', '_')}.json")
    with open(temp_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=4)
        
    return temp_manifest_path

def run_command(command, cwd=None):
    """Executa um comando de shell, exibindo sua saída em tempo real."""
    logging.info(f"Executando comando: {' '.join(command)}")
    
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        # Lê e exibe stdout em tempo real
        for line in process.stdout:
            logging.info(f"[PARSER] {line.strip()}")

        # Lê e exibe stderr após o término
        stderr_output = process.stderr.read()
        if stderr_output:
            logging.error(f"[PARSER STDERR]\n{stderr_output.strip()}")

        process.wait()

        if process.returncode != 0:
            logging.error(f"Comando falhou com código de saída {process.returncode}")
            return False
            
        logging.info("Comando executado com sucesso.")
        return True
    except Exception as e:
        logging.error(f"Falha ao executar o comando: {e}")
        return False

# --- Lógica do Pipeline ---

# ... (resto do arquivo) ...

def main():
    """Função principal para orquestrar o pipeline de ingestão."""
    parser = argparse.ArgumentParser(description="Orquestrador do pipeline de ingestão do Atlas.")
    parser.add_argument("--urn", type=str, help="Processa apenas a URN especificada.")
    parser.add_argument("--limit", type=int, help="Limita o número de fontes a serem processadas.")
    args = parser.parse_args()

    db_conn = get_db_connection()
    if not db_conn:
        sys.exit(1)

    os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)

    try:
        sources_to_process = get_sources_to_process(db_conn, args.urn, args.limit)
        if not sources_to_process:
            logging.info("Nenhuma fonte com status 'PENDENTE' ou 'FALHA' para processar.")
            return

        logging.info(f"Encontradas {len(sources_to_process)} fontes para processar.")
        
        for source in sources_to_process:
            source_id, urn, metadata, source_url = source
            urn_slug = urn.replace(';', '_')
            manifest_path = None
            
            logging.info(f"--- Iniciando pipeline para URN: {urn} ---")

            try:
                # 1. Criar manifesto temporário. 
                # Não há mais download, o parser buscará o texto dos metadados.
                manifest_path = create_temp_manifest(urn, metadata, source_url)
                
                # Define os caminhos de output
                # Define os caminhos de output
                parser_outdir = "src/parser/output"
                parser_output_path = os.path.join(parser_outdir, f"{urn_slug}_structured.json")

                # 2. Executar Parser
                logging.info("ETAPA: Parser - INÍCIO")
                if not run_command(["python3", "-u", "-m", "src.parser.main", "--manifest", manifest_path, "--outdir", parser_outdir]):
                    raise Exception("Falha na etapa do Parser.")
                logging.info("ETAPA: Parser - FIM")

                # 3. Executar Loader (consumindo a saída do parser diretamente)
                logging.info("ETAPA: Loader - INÍCIO")
                if not run_command(["python3", "-m", "src.loader.loader", "--input", parser_output_path]):
                    raise Exception("Falha na etapa do Loader.")
                logging.info("ETAPA: Loader - FIM")
                
                # 5. Executar Linker (assumindo que ele busca dados do DB)
                logging.info("ETAPA: Linker - INÍCIO")
                if not run_command(["python3", "-m", "src.linker.main", "--urn", urn]):
                     raise Exception("Falha na etapa do Linker.")
                logging.info("ETAPA: Linker - FIM")

                # 6. Executar Temporal Validator (assumindo que ele busca dados do DB)
                logging.info("ETAPA: Validador Temporal - INÍCIO")
                if not run_command(["python3", "-m", "src.temporal_validator.validator", "--urn", urn]):
                     raise Exception("Falha na etapa do Validador Temporal.")
                logging.info("ETAPA: Validador Temporal - FIM")

                # 7. Se tudo deu certo, atualizar status
                update_source_status(db_conn, source_id, "PROCESSADO")
                logging.info(f"--- Pipeline para URN: {urn} concluído com sucesso ---")

            except Exception as e:
                logging.error(f"Pipeline falhou para a URN {urn}: {e}")
                update_source_status(db_conn, source_id, "FALHA")
            
            finally:
                # 8. Limpar manifesto temporário
                if manifest_path and os.path.exists(manifest_path):
                    os.remove(manifest_path)

    finally:
        db_conn.close()
        logging.info("Conexão com o PostgreSQL fechada.")

if __name__ == "__main__":
    main()
