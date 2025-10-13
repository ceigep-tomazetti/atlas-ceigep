
import json
import os
import argparse
import psycopg2
from neo4j import GraphDatabase
from datetime import datetime

# --- Configuração do Banco de Dados ---
# As senhas são as mesmas definidas no docker-compose.yml
POSTGRES_CONFIG = {
    "dbname": "atlas_db",
    "user": "atlas_user",
    "password": "atlas_password",
    "host": "localhost",
    "port": "5432"
}
NEO4J_CONFIG = {
    "uri": "neo4j://localhost:7687",
    "user": "neo4j",
    "password": "atlas_password"
}

# --- Lógica de Carga ---

def insert_postgres(conn, data):
    print("Iniciando carga no PostgreSQL...")
    cursor = conn.cursor()
    
    # 1. Inserir Ato Normativo
    ato = data['ato_normativo']
    cursor.execute(
        """INSERT INTO ato_normativo (urn_lexml, tipo_ato, titulo, ementa, entidade_federativa, orgao_publicador, data_publicacao, fonte_oficial, situacao_vigencia) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (ato['urn_lexml'], ato['tipo_ato'], ato['titulo'], ato.get('ementa'), ato['entidade_federativa'], ato['orgao_publicador'], ato['data_publicacao'], ato['fonte_oficial'], ato['situacao_vigencia'])
    )
    ato_id = cursor.fetchone()[0]
    print(f"Ato Normativo inserido com ID: {ato_id}")

    # 2. Inserir Dispositivos e Versões (recursivamente)
    def insert_dispositivos_recursivo(dispositivos, parent_id):
        for disp in dispositivos:
            cursor.execute(
                """INSERT INTO dispositivo (ato_id, parent_id, rotulo, tipo_dispositivo, caminho_estrutural, ordem) 
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (ato_id, parent_id, disp['rotulo'], disp['tipo_dispositivo'], disp['caminho_estrutural'], disp['ordem'])
            )
            disp_id = cursor.fetchone()[0]

            for versao in disp['versoes']:
                cursor.execute(
                    """INSERT INTO versao_textual (dispositivo_id, vigencia_inicio, vigencia_fim, texto_original, texto_normalizado, hash_texto_normalizado, status_vigencia, texto_normalizado_tsv) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, to_tsvector('portuguese', %s))""",
                    (disp_id, versao['vigencia_inicio'], versao.get('vigencia_fim'), versao.get('texto_original_parser'), versao['texto_normalizado'], versao['hash_texto_normalizado'], versao['status_vigencia'], versao['texto_normalizado'])
                )

            if disp.get('filhos'):
                insert_dispositivos_recursivo(disp['filhos'], disp_id)

    # A chave no JSON é 'dispositivos' (plural) e é uma lista
    if 'dispositivos' in data:
        insert_dispositivos_recursivo(data['dispositivos'], None)
        
    conn.commit()
    cursor.close()
    print("Carga no PostgreSQL concluída.")


def insert_neo4j(driver, data):
    print("Iniciando carga no Neo4j...")
    ato = data['ato_normativo']
    urn_ato = ato['urn_lexml']
    
    with driver.session() as session:
        # 1. Criar nó do Ato Normativo
        session.run("CREATE (a:AtoNormativo {urn_lexml: $urn, titulo: $titulo, tipo_ato: $tipo_ato})", 
                    urn=urn_ato, titulo=ato['titulo'], tipo_ato=ato['tipo_ato'])
        print(f"Nó AtoNormativo criado para URN: {urn_ato}")

        # 2. Criar Dispositivos e Versões (recursivamente)
        def insert_dispositivos_recursivo(dispositivos, parent_id_unico):
            for disp in dispositivos:
                id_unico_disp = f"{urn_ato}_{disp['caminho_estrutural']}"

                # Criar nó do dispositivo com id_unico
                session.run("""
                    CREATE (d:Dispositivo {
                        id_unico: $id_unico,
                        caminho_estrutural: $caminho,
                        rotulo: $rotulo, 
                        tipo: $tipo
                    })
                    """, id_unico=id_unico_disp, caminho=disp['caminho_estrutural'], rotulo=disp['rotulo'], tipo=disp['tipo_dispositivo'])
                
                # Criar relacionamento com o pai
                if parent_id_unico:
                    session.run("""
                        MATCH (p:Dispositivo {id_unico: $parent_id})
                        MATCH (d:Dispositivo {id_unico: $child_id})
                        CREATE (p)-[:CONTEM]->(d)
                        """, parent_id=parent_id_unico, child_id=id_unico_disp)
                else: # Se não tem pai, o pai é o Ato Normativo
                    session.run("""
                        MATCH (a:AtoNormativo {urn_lexml: $urn})
                        MATCH (d:Dispositivo {id_unico: $child_id})
                        CREATE (a)-[:CONTEM]->(d)
                        """, urn=urn_ato, child_id=id_unico_disp)

                # Criar nó da versão e relacionar
                for versao in disp['versoes']:
                    session.run("""
                        MATCH (d:Dispositivo {id_unico: $id_unico})
                        CREATE (v:VersaoTextual {texto: $texto, hash: $hash, status: $status})
                        CREATE (d)-[:POSSUI_VERSAO]->(v)
                        """, id_unico=id_unico_disp, texto=versao['texto_normalizado'], hash=versao['hash_texto_normalizado'], status=versao['status_vigencia'])

                if disp.get('filhos'):
                    insert_dispositivos_recursivo(disp['filhos'], id_unico_disp)

        # A chave no JSON é 'dispositivos' (plural) e é uma lista
        if 'dispositivos' in data:
            insert_dispositivos_recursivo(data['dispositivos'], None)
            
    print("Carga no Neo4j concluída.")

# --- Função Principal ---
def main(input_path):
    if not os.path.exists(input_path):
        print(f"Erro: Arquivo de entrada não encontrado em {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Conexão com PostgreSQL
    try:
        conn_pg = psycopg2.connect(**POSTGRES_CONFIG)
        insert_postgres(conn_pg, data)
    except psycopg2.Error as e:
        print(f"Erro na carga do PostgreSQL: {e}")
    finally:
        if 'conn_pg' in locals() and conn_pg:
            conn_pg.close()

    # Conexão com Neo4j
    try:
        driver_neo4j = GraphDatabase.driver(NEO4J_CONFIG["uri"], auth=(NEO4J_CONFIG["user"], NEO4J_CONFIG["password"]))
        insert_neo4j(driver_neo4j, data)
    except Exception as e:
        print(f"Erro na carga do Neo4j: {e}")
    finally:
        if 'driver_neo4j' in locals() and driver_neo4j:
            driver_neo4j.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carregador de dados para o Atlas.")
    parser.add_argument("--input", required=True, help="Caminho para o arquivo JSON normalizado de entrada.")
    args = parser.parse_args()
    main(args.input)
