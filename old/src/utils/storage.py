# src/utils/storage.py
import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env na raiz do projeto
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env')))

# --- Configuração do Cliente Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET_NAME = "fontes-documentos"

def get_storage_client():
    """
    Cria e retorna um cliente para interagir com o Supabase Storage.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.error("Credenciais do Supabase (URL ou SERVICE_ROLE_KEY) não encontradas no .env.")
        return None
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logging.info("Cliente do Supabase Storage inicializado com sucesso.")
        return supabase
    except Exception as e:
        logging.error(f"Erro ao inicializar o cliente do Supabase: {e}")
        return None

def upload_file(client: Client, file_content: bytes, destination_path: str):
    """
    Faz o upload de um conteúdo em bytes para um caminho específico no bucket.
    """
    try:
        # A versão atual da biblioteca supabase-py espera o conteúdo em bytes diretamente.
        client.storage.from_(BUCKET_NAME).upload(
            path=destination_path,
            file=file_content,
            file_options={"content-type": "application/octet-stream", "upsert": "true"}
        )
        logging.info(f"Arquivo enviado com sucesso para: {BUCKET_NAME}/{destination_path}")
        return True
    except Exception as e:
        logging.error(f"Erro durante o upload para o Supabase Storage: {e}")
        return False

def download_file(client: Client, source_path: str):
    """
    Faz o download de um arquivo do bucket e retorna seu conteúdo em bytes.
    """
    try:
        response = client.storage.from_(BUCKET_NAME).download(path=source_path)
        logging.info(f"Arquivo baixado com sucesso de: {BUCKET_NAME}/{source_path}")
        return response
    except Exception as e:
        logging.error(f"Erro durante o download do Supabase Storage: {e}")
        return None
