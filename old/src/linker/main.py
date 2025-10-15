# src/linker/main.py
import os
import json
import logging
import argparse
from datetime import datetime
from neo4j import GraphDatabase
from src.utils.db import get_db_connection
from src.preprocessor.main import ai_extract_relations

def get_device_texts(conn_pg, urn=None, limit=None):
    """Busca todas as versões textuais, opcionalmente filtrando por URN e/ou limite."""
    query = """
    SELECT an.urn_lexml, d.caminho_estrutural, vt.texto_original
    FROM ato_normativo an
    JOIN dispositivo d ON an.id = d.ato_id
    JOIN versao_textual vt ON d.id = vt.dispositivo_id
    WHERE vt.texto_original IS NOT NULL AND vt.texto_original != ''
    """
    params = []
    if urn:
        query += " AND an.urn_lexml = %s"
        params.append(urn)
    
    if limit:
        query += " LIMIT %s"
        params.append(limit)

    with conn_pg.cursor() as cur:
        cur.execute(query, tuple(params))
        return cur.fetchall()

def ensure_destination_urn_exists(conn_pg, urn_destino, rel_info):
    """
    Garante que a URN de destino exista nas tabelas fonte_documento e ato_normativo.
    Cria registros placeholder se não existirem.
    """
    # Garante a existência em fonte_documento
    with conn_pg.cursor() as cur:
        cur.execute(
            "INSERT INTO fonte_documento (urn_lexml, url_fonte, status) VALUES (%s, 'desconhecida', 'PENDENTE') ON CONFLICT (urn_lexml) DO NOTHING;",
            (urn_destino,)
        )
    
    # Garante a existência em ato_normativo
    with conn_pg.cursor() as cur:
        ano_str = rel_info.get('urn_destino_ano')
        if ano_str and ano_str.isdigit():
            data_publicacao = f"{ano_str}-01-01"
        else:
            logging.warning(f"Ano inválido ou ausente para URN de destino '{urn_destino}'. Usando ano atual como placeholder.")
            data_publicacao = f"{datetime.now().year}-01-01"

        cur.execute(
            """
            INSERT INTO ato_normativo (urn_lexml, tipo_ato, ementa, fonte_oficial, situacao_vigencia, data_publicacao)
            VALUES (%s, %s, %s, 'desconhecida', 'desconhecida', %s)
            ON CONFLICT (urn_lexml) DO NOTHING;
            """,
            (
                urn_destino,
                rel_info.get("urn_destino_tipo_ato", "desconhecido"),
                f"Ato descoberto por menção em {rel_info.get('urn_origem')}",
                data_publicacao
            )
        )
    conn_pg.commit()

def save_relations_to_postgres(conn_pg, relations):
    """Salva as relações encontradas na tabela relacao_normativa do PostgreSQL."""
    if not relations:
        return

    with conn_pg.cursor() as cur:
        insert_query = """
        INSERT INTO relacao_normativa (ato_origem_id, ato_destino_id, tipo_relacao, propriedades)
        SELECT a1.id, a2.id, %s, %s
        FROM ato_normativo a1, ato_normativo a2
        WHERE a1.urn_lexml = %s AND a2.urn_lexml = %s
        ON CONFLICT (ato_origem_id, ato_destino_id, tipo_relacao) DO NOTHING;
        """
        
        created_count = 0
        for rel in relations:
            propriedades = {
                "caminho_origem": rel["caminho_origem"],
                "texto_encontrado": rel["texto_encontrado"]
            }
            
            cur.execute(insert_query, (
                rel["tipo_relacao"],
                json.dumps(propriedades),
                rel["urn_origem"],
                rel["urn_destino"]
            ))
            if cur.rowcount > 0:
                created_count += 1
    
    conn_pg.commit()
    logging.info(f"{created_count} novas relações salvas no PostgreSQL.")

def create_relations_in_neo4j(driver, relations):
    """Cria as relações no Neo4j."""
    if not relations:
        logging.info("Nenhuma relação para criar no Neo4j.")
        return

    with driver.session() as session:
        # Garante que os nós de destino existam
        for urn_destino in set(r['urn_destino'] for r in relations):
            session.run("MERGE (a:AtoNormativo {urn_lexml: $urn})", urn=urn_destino)

        # Cria as relações
        rel_counts = {}
        for rel in relations:
            id_unico_origem = f"{rel['urn_origem']}_{rel['caminho_origem']}"
            query = f"""
            MATCH (origem:Dispositivo {{id_unico: $id_unico_origem}})
            MATCH (destino:AtoNormativo {{urn_lexml: $urn_destino}})
            MERGE (origem)-[r:{rel['tipo_relacao']}]->(destino)
            ON CREATE SET r.fonte_texto = $texto_encontrado
            """
            result = session.run(query, 
                                 id_unico_origem=id_unico_origem, 
                                 urn_destino=rel['urn_destino'], 
                                 texto_encontrado=rel['texto_encontrado'])
            
            summary = result.consume()
            if summary.counters.relationships_created > 0:
                rel_type = rel['tipo_relacao']
                rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
    
    total_created = sum(rel_counts.values())
    logging.info(f"{total_created} novas arestas criadas no Neo4j: {rel_counts}")

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Processo do Linker (com IA) iniciado.")

    parser = argparse.ArgumentParser(description="Linker de Relações Jurídicas do Atlas com IA.")
    parser.add_argument("--urn", type=str, help="Processa apenas a URN especificada (opcional).")
    parser.add_argument("--limit", type=int, help="Limita o número de dispositivos a serem processados.")
    args = parser.parse_args()

    db_conn = None
    neo4j_driver = None

    try:
        db_conn = get_db_connection()
        
        uri = "neo4j://localhost:7687" # Força localhost para execução local
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "atlas_password")
        neo4j_driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)
        neo4j_driver.verify_connectivity()
        
        logging.info("Buscando textos dos dispositivos no PostgreSQL...")
        textos_dispositivos = get_device_texts(db_conn, args.urn, args.limit)
        logging.info(f"Consulta ao PostgreSQL concluída. {len(textos_dispositivos)} textos encontrados.")

        if not textos_dispositivos:
            logging.warning("Nenhum texto de dispositivo encontrado para processar.")
            return

        all_relations = []
        for urn_origem, caminho_origem, texto in textos_dispositivos:
            try:
                extracted_relations = ai_extract_relations(texto)
                for rel in extracted_relations:
                    # Constrói a URN de destino completa
                    esfera = "br;federal" if "federal" in rel.get("urn_destino_tipo_ato", "") else "br;go;estadual"
                    urn_destino = f"{esfera};{rel['urn_destino_tipo_ato']};{rel['urn_destino_ano']};{rel['urn_destino_numero']}"
                    
                    # Adiciona a relação à lista principal
                    all_relations.append({
                        "urn_origem": urn_origem,
                        "caminho_origem": caminho_origem,
                        "urn_destino": urn_destino,
                        "tipo_relacao": rel["tipo_relacao"],
                        "texto_encontrado": rel["texto_encontrado"]
                    })
                    
                    # Garante que a URN de destino exista na fonte_documento (descoberta de fronteira)
                    ensure_destination_urn_exists(db_conn, urn_destino, rel)

            except Exception as e:
                logging.error(f"Falha ao extrair relações para o dispositivo {urn_origem}/{caminho_origem}: {e}")

        if all_relations:
            save_relations_to_postgres(db_conn, all_relations)
            create_relations_in_neo4j(neo4j_driver, all_relations)

    except Exception as e:
        logging.error(f"Ocorreu um erro no processo do Linker: {e}", exc_info=True)
    finally:
        if db_conn:
            db_conn.close()
        if neo4j_driver:
            neo4j_driver.close()
        logging.info("Processo do Linker (com IA) finalizado.")

if __name__ == "__main__":
    main()
