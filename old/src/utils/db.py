# src/utils/db.py
import os
import psycopg2
import logging
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env na raiz do projeto
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env')))

def get_db_connection():
    """
    Cria e retorna uma conexão com o banco de dados PostgreSQL (Supabase),
    utilizando as credenciais do arquivo .env.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST"),
            dbname=os.getenv("SUPABASE_DB"),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            port=os.getenv("SUPABASE_PORT", "5432")
        )
        logging.info("Conexão com o banco de dados Supabase bem-sucedida.")
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Erro ao conectar ao banco de dados Supabase: {e}")
        return None
