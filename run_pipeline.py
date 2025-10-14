# run_pipeline.py
import psycopg2
import os
import subprocess
import logging
import json
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# --- Configuração ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

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

def get_collected_sources(conn, urn=None):
    """Busca por fontes com status 'COLETADO', opcionalmente filtrando por URN."""
    if urn:
        query = "SELECT id, urn_lexml, caminho_arquivo_local, metadados_fonte FROM fonte_documento WHERE status = 'COLETADO' AND urn_lexml = %s"
        with conn.cursor() as cur:
            cur.execute(query, (urn,))
            return cur.fetchall()
    else:
        with conn.cursor() as cur:
            cur.execute("SELECT id, urn_lexml, caminho_arquivo_local, metadados_fonte FROM fonte_documento WHERE status = 'COLETADO'")
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

# --- Lógica do Pipeline ---
def run_command(command, cwd=None):
    """Executa um comando de shell e retorna True em caso de sucesso."""
    logging.info(f"Executando comando: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        logging.error(f"Comando falhou com código de saída {result.returncode}")
        logging.error(f"STDOUT: {result.stdout}")
        logging.error(f"STDERR: {result.stderr}")
        return False
    logging.info("Comando executado com sucesso.")
    return True

def create_temp_manifest(source_record):
    """Cria um arquivo de manifesto temporário a partir dos dados do banco."""
    _, urn, file_path, metadata = source_record
    
    # O parser espera um manifesto com a estrutura que ele conhece
    manifest_data = {
        "urn_lexml": urn,
        "source_file_path": file_path,
        "tipo_ato": metadata.get("tipo_legislacao"),
        "titulo": metadata.get("ementa"),
        "entidade_federativa": "Estadual", # Hardcoded por enquanto
        "orgao_publicador": metadata.get("autor", "Governo do Estado de Goiás"),
        "data_publicacao": metadata.get("data_legislacao")
    }
    
    temp_manifest_path = os.path.join("tmp_analise", f"temp_manifest_{urn.replace(';', '_')}.json")
    with open(temp_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=4)
        
    return temp_manifest_path

def main():
    """Função principal para orquestrar o pipeline de ingestão."""
    parser = argparse.ArgumentParser(description="Orquestrador do pipeline de ingestão do Atlas.")
    parser.add_argument("--urn", type=str, help="Processa apenas a URN especificada.")
    args = parser.parse_args()

    db_conn = connect_db_postgres()
    if not db_conn:
        sys.exit(1)

    try:
        sources_to_process = get_collected_sources(db_conn, args.urn)
        if not sources_to_process:
            logging.info("Nenhuma fonte com status 'COLETADO' para processar.")
            return

        logging.info(f"Encontradas {len(sources_to_process)} fontes para processar.")
        
        for source in sources_to_process:
            source_id, urn, file_path, _ = source
            urn_slug = urn.replace(';', '_')
            logging.info(f"--- Iniciando pipeline para URN: {urn} ---")

            # 1. Criar manifesto temporário
            manifest_path = create_temp_manifest(source)
            
            # Define os caminhos de output baseados na estrutura 'src'
            parser_outdir = "src/parser/output"
            normalizer_outdir = "src/normalizer/output"
            parser_logdir = "src/parser/logs"
            normalizer_logdir = "src/normalizer/logs"
            
            parser_output = os.path.join(parser_outdir, f"{urn_slug}_recursivo.json")
            normalizer_output = os.path.join(normalizer_outdir, f"{urn_slug}_normalizado.json")

            # 2. Executar Parser
            if not run_command(["python3", "src/parser/main.py", "--manifest", manifest_path, "--outdir", parser_outdir, "--logs", parser_logdir]):
                update_source_status(db_conn, source_id, "FALHA")
                continue

            # 3. Executar Normalizer
            if not run_command(["python3", "src/normalizer/normalizer.py", "--input", parser_output, "--outdir", normalizer_outdir, "--logdir", normalizer_logdir]):
                update_source_status(db_conn, source_id, "FALHA")
                continue

            # 4. Executar Loader
            if not run_command(["python3", "src/loader/loader.py", "--input", normalizer_output]):
                update_source_status(db_conn, source_id, "FALHA")
                continue
            
            # 5. Executar Integrity Checker
            # O checker precisa do manifesto, que já tem o caminho absoluto para o arquivo fonte
            if not run_command(["python3", "src/integrity_checker/checker.py", "--manifest", manifest_path]):
                update_source_status(db_conn, source_id, "FALHA")
                continue

            # 6. Se tudo deu certo, atualizar status
            update_source_status(db_conn, source_id, "PROCESSADO")
            os.remove(manifest_path) # Limpa o manifesto temporário
            logging.info(f"--- Pipeline para URN: {urn} concluído com sucesso ---")

    finally:
        db_conn.close()
        logging.info("Conexão com o PostgreSQL fechada.")

if __name__ == "__main__":
    main()
