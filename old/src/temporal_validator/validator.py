# temporal_validator/validator.py
import os
from neo4j import GraphDatabase
import logging
from src.utils.db import get_db_connection

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def connect_db_neo4j():
    """Conecta ao banco de dados Neo4j."""
    try:
        uri = "neo4j://localhost:7687" # Força localhost para execução local
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "atlas_password")
        driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)
        logging.info("Conexão com o Neo4j bem-sucedida.")
        return driver
    except Exception as e:
        logging.error(f"Erro ao conectar ao Neo4j: {e}")
        return None

def check_internal_coherence(conn_pg):
    """Verifica se existem versões sobrepostas para o mesmo dispositivo."""
    logging.info("Iniciando Checagem 1: Coerência Temporal Interna (Sobreposição de Vigência)...")
    query = """
    SELECT
        d.caminho_estrutural,
        an.urn_lexml,
        v1.id AS versao1_id, v1.vigencia_inicio AS inicio1, v1.vigencia_fim AS fim1,
        v2.id AS versao2_id, v2.vigencia_inicio AS inicio2, v2.vigencia_fim AS fim2
    FROM versao_textual v1
    JOIN versao_textual v2 ON v1.dispositivo_id = v2.dispositivo_id AND v1.id < v2.id
    JOIN dispositivo d ON v1.dispositivo_id = d.id
    JOIN ato_normativo an ON d.ato_id = an.id
    WHERE (v1.vigencia_inicio, COALESCE(v1.vigencia_fim, 'infinity')) OVERLAPS
          (v2.vigencia_inicio, COALESCE(v2.vigencia_fim, 'infinity'));
    """
    with conn_pg.cursor() as cur:
        cur.execute(query)
        results = cur.fetchall()
    
    if not results:
        logging.info("SUCESSO: Nenhuma sobreposição de vigência encontrada.")
        return True
    else:
        logging.error(f"FALHA: Encontradas {len(results)} sobreposições de vigência:")
        for row in results:
            logging.error(f"  - Conflito em {row[1]}::{row[0]}: Versões {row[2]} e {row[5]} se sobrepõem.")
        return False

def check_external_coherence(conn_pg, driver_neo4j):
    """Verifica se a data de um ato alterador é anterior à do ato alterado."""
    logging.info("Iniciando Checagem 2: Coerência Temporal Externa (Relações)...")
    
    # 1. Buscar todas as relações do Neo4j
    with driver_neo4j.session() as session:
        result = session.run("""
        MATCH (d:Dispositivo)-[r:ALTERA|REVOGA]->(a:AtoNormativo)
        RETURN d.id_unico AS id_origem, a.urn_lexml AS urn_destino
        """)
        relations = [(record["id_origem"], record["urn_destino"]) for record in result]
    
    if not relations:
        logging.info("Nenhuma relação :ALTERA ou :REVOGA encontrada para verificar.")
        return True

    # 2. Buscar datas de publicação do PostgreSQL
    urns = set()
    for id_origem, urn_destino in relations:
        urns.add(id_origem.split('_')[0])
        urns.add(urn_destino)
    
    with conn_pg.cursor() as cur:
        cur.execute("SELECT urn_lexml, data_publicacao FROM ato_normativo WHERE urn_lexml = ANY(%s)", (list(urns),))
        dates = {urn: date for urn, date in cur.fetchall()}

    # 3. Comparar as datas
    inconsistencies = []
    for id_origem, urn_destino in relations:
        urn_origem = id_origem.split('_')[0]
        date_origem = dates.get(urn_origem)
        date_destino = dates.get(urn_destino)

        if date_origem and date_destino and date_destino < date_origem:
            inconsistencies.append((urn_origem, date_origem, urn_destino, date_destino))

    if not inconsistencies:
        logging.info("SUCESSO: Nenhuma inconsistência temporal encontrada nas relações.")
        return True
    else:
        logging.error(f"FALHA: Encontradas {len(inconsistencies)} inconsistências temporais:")
        for o_urn, o_date, d_urn, d_date in inconsistencies:
            logging.error(f"  - Ato '{d_urn}' ({d_date}) não pode alterar/revogar o ato '{o_urn}' ({o_date}) que é mais recente.")
        return False

def main():
    """Função principal para orquestrar as validações."""
    conn_pg = get_db_connection()
    driver_neo4j = connect_db_neo4j()

    if not conn_pg or not driver_neo4j:
        logging.error("Não foi possível conectar a um ou mais bancos de dados. Encerrando.")
        return

    try:
        print("\n" + "="*50)
        internal_ok = check_internal_coherence(conn_pg)
        print("="*50 + "\n")
        
        print("="*50)
        external_ok = check_external_coherence(conn_pg, driver_neo4j)
        print("="*50 + "\n")

        print("--- Relatório Final de Coerência Temporal ---")
        if internal_ok and external_ok:
            print("✅ APROVADO: Nenhuma inconsistência temporal encontrada.")
        else:
            print("❌ REPROVADO: Foram encontradas inconsistências temporais. Verifique os logs de erro acima.")

    finally:
        if conn_pg: conn_pg.close()
        if driver_neo4j: driver_neo4j.close()
        logging.info("Conexões com os bancos de dados fechadas.")

if __name__ == "__main__":
    main()
