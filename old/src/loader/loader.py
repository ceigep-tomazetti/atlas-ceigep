"""
Módulo Loader: Carrega os dados estruturados pelo parser nos bancos de dados
PostgreSQL (Supabase) e Neo4j.

Este script foi refatorado para consumir a saída da arquitetura de parser
"Segmentar e Conquistar" (schemas.py).
"""
import json
import os
import argparse
import psycopg2
import hashlib
from neo4j import GraphDatabase
from datetime import datetime
import sys
from src.utils.db import get_db_connection

# --- Configuração ---
NEO4J_CONFIG = {
    "uri": "neo4j://localhost:7687",
    "user": "neo4j",
    "password": "atlas_password"
}

def get_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# --- Lógica de Carga PostgreSQL ---

def insert_postgres(conn, data):
    """Carrega os dados do JSON estruturado no banco de dados PostgreSQL."""
    print("Iniciando carga no PostgreSQL...")
    cursor = conn.cursor()
    
    doc = data['documento']
    urn = doc['id']
    
    # 1. Limpeza idempotente
    print(f"Limpando dados antigos para a URN: {urn}...")
    cursor.execute("DELETE FROM ato_normativo WHERE urn_lexml = %s", (urn,))
    print("Limpeza concluída.")

    # 2. Inserir Ato Normativo
    # Extrai metadados do documento e do manifesto aninhado para garantir a completude
    manifesto = data.get('manifesto', {}) # Assume que o manifesto pode estar aninhado
    
    # Converte a data para o formato YYYY-MM-DD antes de inserir
    data_publicacao_str = manifesto.get('data_publicacao')
    try:
        data_publicacao = datetime.strptime(data_publicacao_str, '%d/%m/%Y').strftime('%Y-%m-%d') if data_publicacao_str else None
    except ValueError:
        data_publicacao = data_publicacao_str # Assume que já está no formato correto
    
    if not data_publicacao:
        data_publicacao = datetime.now().strftime('%Y-%m-%d')


    cursor.execute(
        """INSERT INTO ato_normativo (urn_lexml, tipo_ato, titulo, ementa, entidade_federativa, orgao_publicador, data_publicacao, fonte_oficial, situacao_vigencia) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (
            urn,
            manifesto.get('tipo_ato', 'decreto'),
            doc['rotulo'],
            doc.get('cabecalho', {}).get('ementa'),
            manifesto.get('entidade_federativa', 'Estadual'),
            manifesto.get('orgao_publicador', 'Governo do Estado de Goiás'),
            data_publicacao,
            manifesto.get('source_url', 'desconhecida'),
            manifesto.get('situacao_vigencia', 'vigente')
        )
    )
    ato_id = cursor.fetchone()[0]
    print(f"Ato Normativo inserido com ID: {ato_id}")

    # 3. Inserir Dispositivos e Versões a partir da nova estrutura
    order_counter = 0
    def insert_dispositivo(item, tipo, parent_id, caminho_prefixo):
        nonlocal order_counter
        order_counter += 1
        
        caminho_estrutural = f"{caminho_prefixo}/{tipo}:{item['rotulo']}"
        texto = item.get('caput') or item.get('texto')
        
        cursor.execute(
            """INSERT INTO dispositivo (ato_id, parent_id, rotulo, tipo_dispositivo, caminho_estrutural, ordem) 
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (ato_id, parent_id, item['rotulo'], tipo, caminho_estrutural, order_counter)
        )
        disp_id = cursor.fetchone()[0]

        # Cada dispositivo agora tem uma única versão textual implícita
        cursor.execute(
            """INSERT INTO versao_textual (dispositivo_id, vigencia_inicio, texto_original, texto_normalizado, hash_texto_normalizado, status_vigencia, texto_normalizado_tsv) 
               VALUES (%s, %s, %s, %s, %s, 'vigente', to_tsvector('public.portuguese_unaccent', %s))""",
            (disp_id, data_publicacao, texto, texto, get_sha256(texto), texto)
        )
        return disp_id, caminho_estrutural

    # Itera sobre a estrutura aninhada do parser
    for artigo in doc.get('corpo', []):
        artigo_id, artigo_path = insert_dispositivo(artigo, 'artigo', None, 'corpo')
        
        for paragrafo in artigo.get('paragrafos', []):
            par_id, par_path = insert_dispositivo(paragrafo, 'paragrafo', artigo_id, artigo_path)
            # Incisos dentro de parágrafos
            for inciso in paragrafo.get('incisos', []):
                inc_id, inc_path = insert_dispositivo(inciso, 'inciso', par_id, par_path)
                for alinea in inciso.get('alineas', []):
                    ali_id, ali_path = insert_dispositivo(alinea, 'alinea', inc_id, inc_path)
                    for item in alinea.get('itens', []):
                        insert_dispositivo(item, 'item', ali_id, ali_path)

        # Incisos direto no artigo
        for inciso in artigo.get('incisos', []):
            inc_id, inc_path = insert_dispositivo(inciso, 'inciso', artigo_id, artigo_path)
            for alinea in inciso.get('alineas', []):
                ali_id, ali_path = insert_dispositivo(alinea, 'alinea', inc_id, inc_path)
                for item in alinea.get('itens', []):
                    insert_dispositivo(item, 'item', ali_id, ali_path)

    conn.commit()
    cursor.close()
    print("Carga no PostgreSQL concluída.")
    return ato_id

# --- Lógica de Carga Neo4j ---

def insert_neo4j(driver, data):
    """Carrega os dados do JSON estruturado no banco de dados Neo4j."""
    print("Iniciando carga no Neo4j...")
    doc = data['documento']
    urn_ato = doc['id']

    with driver.session() as session:
        # 1. Limpeza idempotente
        print(f"Limpando dados antigos do Neo4j para a URN: {urn_ato}...")
        session.run("MATCH (a:AtoNormativo {urn_lexml: $urn}) DETACH DELETE a", urn=urn_ato)
        print("Limpeza do Neo4j concluída.")

        # 2. Criar nó do Ato Normativo
        session.run("CREATE (a:AtoNormativo {urn_lexml: $urn, titulo: $titulo})", 
                    urn=urn_ato, titulo=doc['rotulo'])
        print(f"Nó AtoNormativo criado para URN: {urn_ato}")

        # 3. Criar Dispositivos e Versões
        def create_node_and_rel(item, tipo, parent_urn, caminho_prefixo):
            caminho_estrutural = f"{caminho_prefixo}/{tipo}:{item['rotulo']}"
            id_unico = f"{urn_ato}#{caminho_estrutural}"
            texto = item.get('caput') or item.get('texto')

            # Cria o nó do dispositivo
            session.run("""
                CREATE (d:Dispositivo {id_unico: $id_unico, caminho_estrutural: $caminho, rotulo: $rotulo, tipo: $tipo})
                """, id_unico=id_unico, caminho=caminho_estrutural, rotulo=item['rotulo'], tipo=tipo)
            
            # Cria a relação com o pai
            session.run("""
                MATCH (p {urn_lexml: $parent_urn})
                MATCH (c:Dispositivo {id_unico: $child_id})
                CREATE (p)-[:CONTEM]->(c)
                """, parent_urn=parent_urn, child_id=id_unico)

            # Cria a versão textual
            session.run("""
                MATCH (d:Dispositivo {id_unico: $id_unico})
                CREATE (v:VersaoTextual {hash: $hash, texto: $texto})
                CREATE (d)-[:POSSUI_VERSAO]->(v)
                """, id_unico=id_unico, hash=get_sha256(texto), texto=texto)
            
            return id_unico

        for artigo in doc.get('corpo', []):
            artigo_urn = create_node_and_rel(artigo, 'artigo', urn_ato, 'corpo')
            
            for paragrafo in artigo.get('paragrafos', []):
                par_urn = create_node_and_rel(paragrafo, 'paragrafo', artigo_urn, 'paragrafo')
                for inciso in paragrafo.get('incisos', []):
                    inc_urn = create_node_and_rel(inciso, 'inciso', par_urn, 'inciso')
                    # ... e assim por diante para alíneas e itens

            for inciso in artigo.get('incisos', []):
                inc_urn = create_node_and_rel(inciso, 'inciso', artigo_urn, 'inciso')
                # ... e assim por diante para alíneas e itens

    print("Carga no Neo4j concluída.")


# --- Função Principal ---
def main(input_path):
    if not os.path.exists(input_path):
        print(f"Erro: Arquivo de entrada não encontrado em {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn_pg = None
    driver_neo4j = None
    try:
        # Conexão com PostgreSQL
        conn_pg = get_db_connection()
        insert_postgres(conn_pg, data)
        
        # Conexão com Neo4j
        driver_neo4j = GraphDatabase.driver(
            NEO4J_CONFIG["uri"], 
            auth=(NEO4J_CONFIG["user"], NEO4J_CONFIG["password"]),
            encrypted=False
        )
        insert_neo4j(driver_neo4j, data)

    except Exception as e:
        print(f"Erro durante a execução do loader: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn_pg: conn_pg.close()
        if driver_neo4j: driver_neo4j.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carregador de dados para o Atlas.")
    parser.add_argument("--input", required=True, help="Caminho para o arquivo JSON estruturado de entrada.")
    args = parser.parse_args()
    main(args.input)