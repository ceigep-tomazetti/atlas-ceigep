
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import psycopg2
from neo4j import GraphDatabase
from src.utils.db import get_db_connection

VERSION = "1.0"

def get_ground_truth(json_path):
    """Lê o arquivo JSON de verdade e extrai os dados para verificação."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    urn_lexml = data['ato_normativo'].get('urn_lexml')
    dispositivos_list = []

    def recurse_devices(device_node):
        dispositivos_list.append(device_node)
        for child in device_node.get('filhos', []):
            recurse_devices(child)

    if 'dispositivos' in data:
        for root_device in data['dispositivos']:
            recurse_devices(root_device)

    device_count = len(dispositivos_list)
    version_count = device_count
    hash_set = {
        d.get('versoes', [{}])[0].get('hash_texto_normalizado') 
        for d in dispositivos_list 
        if d.get('versoes', [{}])[0].get('hash_texto_normalizado')
    }

    device_count = len(dispositivos_list)
    version_count = device_count
    hash_set = {
        d.get('versoes', [{}])[0].get('hash_texto_normalizado') 
        for d in dispositivos_list 
        if d.get('versoes', [{}])[0].get('hash_texto_normalizado')
    }

    return {
        "urn_lexml": urn_lexml,
        "device_count": device_count,
        "version_count": version_count,
        "hash_set": hash_set,
    }

def check_postgres(ground_truth):
    """Verifica a integridade dos dados no PostgreSQL."""
    results = {}
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query_count = "SELECT COUNT(*) FROM dispositivo WHERE ato_id = (SELECT id FROM ato_normativo WHERE urn_lexml = %s);"
        cur.execute(query_count, (ground_truth['urn_lexml'],))
        pg_device_count = cur.fetchone()[0]
        results['device_count'] = pg_device_count
        results['device_count_match'] = (ground_truth['device_count'] == pg_device_count)

        query_hashes = """
            SELECT vt.hash_texto_normalizado AS h
            FROM versao_textual vt
            JOIN dispositivo d ON d.id = vt.dispositivo_id
            WHERE d.ato_id = (SELECT id FROM ato_normativo WHERE urn_lexml = %s);
        """
        cur.execute(query_hashes, (ground_truth['urn_lexml'],))
        pg_hashes = {row[0] for row in cur.fetchall()}
        results['hash_set'] = pg_hashes
        results['hash_set_match'] = (ground_truth['hash_set'] == pg_hashes)
        
        results['missing_hashes_in_pg'] = ground_truth['hash_set'] - pg_hashes
        results['extra_hashes_in_pg'] = pg_hashes - ground_truth['hash_set']

        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Erro no PostgreSQL: {error}", file=sys.stderr)
        return None
    finally:
        if conn is not None:
            conn.close()
    return results

def check_neo4j(ground_truth):
    """Verifica a integridade dos dados no Neo4j."""
    results = {}
    driver = None
    try:
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        with driver.session() as session:
            query_count = "MATCH (a:AtoNormativo {urn_lexml: $urn})-[:CONTEM*1..]->(d:Dispositivo) RETURN COUNT(DISTINCT d) AS total_dispositivos;"
            result = session.run(query_count, urn=ground_truth['urn_lexml'])
            neo4j_device_count = result.single()['total_dispositivos']
            results['device_count'] = neo4j_device_count
            results['device_count_match'] = (ground_truth['device_count'] == neo4j_device_count)

            query_hashes = "MATCH (a:AtoNormativo {urn_lexml: $urn})-[:CONTEM*1..]->(:Dispositivo)-[:POSSUI_VERSAO]->(v:VersaoTextual) RETURN collect(DISTINCT v.hash) AS hashes;"
            result = session.run(query_hashes, urn=ground_truth['urn_lexml'])
            neo4j_hashes = set(result.single()['hashes'])
            results['hash_set'] = neo4j_hashes
            results['hash_set_match'] = (ground_truth['hash_set'] == neo4j_hashes)
            
            results['missing_hashes_in_neo4j'] = ground_truth['hash_set'] - neo4j_hashes
            results['extra_hashes_in_neo4j'] = neo4j_hashes - ground_truth['hash_set']

    except Exception as error:
        print(f"Erro no Neo4j: {error}", file=sys.stderr)
        return None
    finally:
        if driver is not None:
            driver.close()
    return results

def generate_report(ground_truth, pg_results, neo4j_results, json_path, duration):
    """Gera o relatório de integridade em Markdown de forma robusta."""
    urn = ground_truth['urn_lexml']
    urn_slug = urn.replace(';', '_')
    output_dir = "src/integrity_checker/output"
    os.makedirs(output_dir, exist_ok=True)
    
    report_path = os.path.join(output_dir, f"{urn_slug}_integrity_report.md")
    log_path = os.path.join(output_dir, f"{urn_slug}_integrity_log.jsonl")

    pg_pass = pg_results and pg_results['device_count_match'] and pg_results['hash_set_match']
    neo4j_pass = neo4j_results and neo4j_results['device_count_match'] and neo4j_results['hash_set_match']
    overall_pass = pg_pass and neo4j_pass

    lines = []
    lines.append(f"# Relatório de Integridade: {urn}")
    lines.append(f"\n**Data da Verificação:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Versão do Checker:** {VERSION}")
    lines.append(f"**Duração:** {duration:.2f} segundos")
    lines.append(f"**Arquivo Fonte:** {json_path}")
    lines.append(f"\n## Resumo")
    lines.append(f"* **Status Geral:** {'PASS' if overall_pass else 'FAIL'}")
    lines.append("\n---")
    lines.append("\n## PostgreSQL")
    lines.append(f"* **Status:** {'PASS' if pg_pass else 'FAIL'}")
    lines.append(f"* **Contagem de Dispositivos:** {'PASS' if pg_results['device_count_match'] else 'FAIL'}")
    lines.append(f"  * Esperado (JSON): {ground_truth['device_count']}")
    lines.append(f"  * Encontrado (PG): {pg_results['device_count']}")
    lines.append(f"* **Integridade dos Hashes:** {'PASS' if pg_results['hash_set_match'] else 'FAIL'}")
    lines.append(f"  * Hashes no JSON: {len(ground_truth['hash_set'])}")
    lines.append(f"  * Hashes no PG: {len(pg_results['hash_set'])}")
    lines.append(f"  * Correspondentes: {len(ground_truth['hash_set'].intersection(pg_results['hash_set']))}")

    if not pg_results['hash_set_match']:
        if pg_results['missing_hashes_in_pg']:
            lines.append(f"  * Hashes Faltando no PG: {len(pg_results['missing_hashes_in_pg'])}")
        if pg_results['extra_hashes_in_pg']:
            lines.append(f"  * Hashes Extras no PG: {len(pg_results['extra_hashes_in_pg'])}")

    lines.append("\n---")
    lines.append("\n## Neo4j")
    lines.append(f"* **Status:** {'PASS' if neo4j_pass else 'FAIL'}")
    lines.append(f"* **Contagem de Dispositivos:** {'PASS' if neo4j_results['device_count_match'] else 'FAIL'}")
    lines.append(f"  * Esperado (JSON): {ground_truth['device_count']}")
    lines.append(f"  * Encontrado (Neo4j): {neo4j_results['device_count']}")
    lines.append(f"* **Integridade dos Hashes:** {'PASS' if neo4j_results['hash_set_match'] else 'FAIL'}")
    lines.append(f"  * Hashes no JSON: {len(ground_truth['hash_set'])}")
    lines.append(f"  * Hashes no Neo4j: {len(neo4j_results['hash_set'])}")
    lines.append(f"  * Correspondentes: {len(ground_truth['hash_set'].intersection(neo4j_results['hash_set']))}")

    if not neo4j_results['hash_set_match']:
        if neo4j_results['missing_hashes_in_neo4j']:
            lines.append(f"  * Hashes Faltando no Neo4j: {len(neo4j_results['missing_hashes_in_neo4j'])}")
        if neo4j_results['extra_hashes_in_neo4j']:
            lines.append(f"  * Hashes Extras no Neo4j: {len(neo4j_results['extra_hashes_in_neo4j'])}")

    report_content = "\n".join(lines)
    with open(report_path, 'w') as f:
        f.write(report_content)
    print(f"Relatório gerado em: {report_path}")

    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "urn": urn,
        "status": "PASS" if overall_pass else "FAIL",
        "duration_seconds": duration,
        "ground_truth": {
            "device_count": ground_truth['device_count'],
            "hash_count": len(ground_truth['hash_set'])
        },
        "postgres": {
            "status": "PASS" if pg_pass else "FAIL",
            "device_count": pg_results['device_count'],
            "hash_count": len(pg_results['hash_set']),
            "device_count_match": pg_results['device_count_match'],
            "hash_set_match": pg_results['hash_set_match']
        },
        "neo4j": {
            "status": "PASS" if neo4j_pass else "FAIL",
            "device_count": neo4j_results['device_count'],
            "hash_count": len(neo4j_results['hash_set']),
            "device_count_match": neo4j_results['device_count_match'],
            "hash_set_match": neo4j_results['hash_set_match']
        }
    }
    with open(log_path, 'w') as f:
        json.dump(log_data, f)
        f.write('\n')

    return overall_pass

def main():
    """Função principal para executar o verificador de integridade."""
    parser = argparse.ArgumentParser(description="Verificador de Integridade para o Atlas.")
    parser.add_argument("--manifest", required=True, help="Caminho para o arquivo de manifesto JSON.")
    args = parser.parse_args()

    start_time = datetime.now()
    
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

    with open(args.manifest, 'r') as f:
        config = json.load(f)
    
    urn = config['urn_lexml']
    normalized_file_name = urn.replace(";", "_") + "_normalizado.json"
    json_path = os.path.join("src/normalizer/output", normalized_file_name)

    if not os.path.exists(json_path):
        print(f"Erro: Arquivo normalizado não encontrado em '{json_path}'", file=sys.stderr)
        sys.exit(1)

    print(f"Iniciando verificação para: {json_path}")
    print("1. Extraindo dados do JSON...")
    ground_truth = get_ground_truth(json_path)
    print(f"   - URN: {ground_truth['urn_lexml']}")
    print(f"   - Dispositivos: {ground_truth['device_count']}")
    print(f"   - Hashes únicos: {len(ground_truth['hash_set'])}")

    print("\n2. Verificando PostgreSQL...")
    pg_results = check_postgres(ground_truth)
    if pg_results:
        print("   - Verificação do PostgreSQL concluída.")
    else:
        print("   - Falha na verificação do PostgreSQL.")
        sys.exit(1)

    print("\n3. Verificando Neo4j...")
    neo4j_results = check_neo4j(ground_truth)
    if neo4j_results:
        print("   - Verificação do Neo4j concluída.")
    else:
        print("   - Falha na verificação do Neo4j.")
        sys.exit(1)

    print("\n4. Gerando relatório...")
    duration = (datetime.now() - start_time).total_seconds()
    success = generate_report(ground_truth, pg_results, neo4j_results, json_path, duration)

    if not success:
        print("\nVerificação de integridade FALHOU.", file=sys.stderr)
        sys.exit(1)
    
    print("\nVerificação de integridade CONCLUÍDA com sucesso.")

if __name__ == "__main__":
    main()
