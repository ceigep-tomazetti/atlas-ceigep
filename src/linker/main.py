# linker/main.py
import os
import psycopg2
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging
import re
import spacy

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def connect_db_postgres():
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

def connect_db_neo4j():
    """Conecta ao banco de dados Neo4j."""
    try:
        uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        logging.info("Conexão com o Neo4j bem-sucedida.")
        return driver
    except Exception as e:
        logging.error(f"Erro ao conectar ao Neo4j: {e}")
        return None

def fetch_all_versions_with_urn(conn_pg):
    """Busca todas as versões textuais junto com a URN do seu ato normativo."""
    query = """
    SELECT 
        vt.id, 
        vt.texto_original,
        d.caminho_estrutural,
        an.urn_lexml
    FROM versao_textual vt
    JOIN dispositivo d ON vt.dispositivo_id = d.id
    JOIN ato_normativo an ON d.ato_id = an.id
    WHERE vt.texto_original IS NOT NULL;
    """
    with conn_pg.cursor() as cur:
        cur.execute(query)
        records = cur.fetchall()
        logging.info(f"Encontradas {len(records)} versões textuais com texto original para análise.")
        return records

def find_and_parse_mentions(records, nlp):
    """Encontra e analisa menções de alteração, revogação, regulamentação e remissão."""
    pattern = re.compile(
        r"(?P<altera>(?:redação dada pel[ao]\s|a\s)(?P<tipo_ato_alt>[^,]+?)\s+nº\s+(?P<numero_alt>[\d\.]+),\s+de\s+(?P<data_alt>(?:\d{1,2}\s+de\s+\w+\s+de\s+)?\d{4}))"
        r"|"
        r"(?P<revoga>revogad[ao]\s+pela\s+(?P<tipo_ato_rev>[^,]+?)\s+n[oº]\s+(?P<numero_rev>[\d\.]+),\s+de\s+(?P<data_rev>[\d\-]+))"
        r"|"
        r"(?P<regulamenta>Regulamentado\s+pelo\s+(?P<tipo_ato_reg>Decreto)\s+n[oº]\s+(?P<numero_reg>[\d\.]+),\s+de\s+(?P<data_reg>[\d\-]+))"
        r"|"
        r"(?P<remete>\(Vide\s+(?P<tipo_ato_rem>Lei|Decreto-Lei)\s+nº\s+(?P<numero_rem>[\d\.]+),\s+de\s+(?P<data_rem>\d{4})\))",
        re.IGNORECASE
    )
    
    parsed_mentions = []
    for record_id, text, path, urn in records:
        matches = pattern.finditer(text)
        for match in matches:
            if match.group("altera"):
                tipo_relacao, tipo_ato_bruto, numero, data_str = "ALTERA", match.group("tipo_ato_alt"), match.group("numero_alt"), match.group("data_alt")
            elif match.group("revoga"):
                tipo_relacao, tipo_ato_bruto, numero, data_str = "REVOGA", match.group("tipo_ato_rev"), match.group("numero_rev"), match.group("data_rev")
            elif match.group("regulamenta"):
                tipo_relacao, tipo_ato_bruto, numero, data_str = "REGULAMENTA", match.group("tipo_ato_reg"), match.group("numero_reg"), match.group("data_reg")
            elif match.group("remete"):
                tipo_relacao, tipo_ato_bruto, numero, data_str = "REMETE_A", match.group("tipo_ato_rem"), match.group("numero_rem"), match.group("data_rem")
            else:
                continue

            ano_match = re.search(r'(\d{4})', data_str)
            ano = ano_match.group(1) if ano_match else data_str.split('-')[-1]

            if not ano.isdigit() or len(ano) != 4: continue

            tipo_ato_norm = tipo_ato_bruto.strip().lower().replace(" ", ".")
            esfera = "br;federal" if "constitucional" in tipo_ato_norm or tipo_relacao == "REMETE_A" else "br;go;estadual"
            urn_destino = f"{esfera};{tipo_ato_norm};{ano};{numero.replace('.', '')}"
            
            mention = {
                "urn_origem": urn, "caminho_origem": path, "urn_destino": urn_destino,
                "tipo_relacao": tipo_relacao, "texto_encontrado": match.group(0)
            }
            parsed_mentions.append(mention)
            
    return parsed_mentions

def create_relations_in_neo4j(driver, relations):
    """Cria as relações (ALTERA, REVOGA, etc.) no Neo4j de forma segura."""
    if not relations:
        logging.info("Nenhuma relação para criar no Neo4j.")
        return

    with driver.session() as session:
        rel_counts = {}
        for rel in relations:
            id_unico_origem = f"{rel['urn_origem']}_{rel['caminho_origem']}"
            
            rel_type = rel['tipo_relacao']
            if rel_type not in ["ALTERA", "REVOGA", "REGULAMENTA", "REMETE_A"]:
                logging.warning(f"Tipo de relação inválido ignorado: {rel_type}")
                continue

            query = f"""
            MATCH (origem:Dispositivo {{id_unico: $id_unico_origem}})
            MERGE (destino:AtoNormativo {{urn_lexml: $urn_destino}})
            MERGE (origem)-[r:{rel_type}]->(destino)
            ON CREATE SET r.fonte_texto = $texto_encontrado
            """
            result = session.run(query, 
                                 id_unico_origem=id_unico_origem, 
                                 urn_destino=rel['urn_destino'], 
                                 texto_encontrado=rel['texto_encontrado'])
            
            summary = result.consume()
            if summary.counters.relationships_created > 0:
                rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
    
    total_created = sum(rel_counts.values())
    logging.info(f"Processadas {len(relations)} relações. {total_created} novas arestas criadas: {rel_counts}")


def main():
    """Função principal para orquestrar a detecção e criação de relações."""
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    os.environ.setdefault("NEO4J_PASSWORD", "atlas_password")

    conn_pg = connect_db_postgres()
    driver_neo4j = connect_db_neo4j()

    if not conn_pg or not driver_neo4j:
        logging.error("Falha na conexão com um ou mais bancos de dados. Encerrando.")
        return

    try:
        logging.info("Carregando modelo spaCy 'pt_core_news_sm'...")
        nlp = spacy.load('pt_core_news_sm')
        logging.info("Modelo carregado.")

        versions = fetch_all_versions_with_urn(conn_pg)
        relations_to_create = find_and_parse_mentions(versions, nlp)
        
        if relations_to_create:
            logging.info(f"Encontradas e analisadas {len(relations_to_create)} potenciais relações.")
            create_relations_in_neo4j(driver_neo4j, relations_to_create)
        else:
            logging.info("Nenhuma menção de alteração encontrada para processar.")

    finally:
        if conn_pg:
            conn_pg.close()
            logging.info("Conexão com o PostgreSQL fechada.")
        if driver_neo4j:
            driver_neo4j.close()
            logging.info("Conexão com o Neo4j fechada.")

if __name__ == "__main__":
    main()
