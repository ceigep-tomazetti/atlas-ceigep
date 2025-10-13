import boto3
import json
import hashlib
import os
import re
import argparse
import fitz  # PyMuPDF
import sys
from bs4 import BeautifulSoup
from datetime import datetime
from uuid import uuid4

# --- Configuração Global ---
# Removido - agora via CLI/env
PARSER_VERSION = "2.0"

DEVICE_PATTERNS = [
    {"tipo": "paragrafo", "level": 1, "slug": "par", "regex": r"(?im)^\s*(§\s*\d+|Parágrafo\s+único)"},
    {"tipo": "inciso",    "level": 2, "slug": "inc", "regex": r"(?im)^([IVXLCDM]+)\s*[-–]"},
    {"tipo": "alinea",    "level": 3, "slug": "ali", "regex": r"(?im)^([a-z])\)"},
    {"tipo": "item",      "level": 4, "slug": "item", "regex": r"(?im)^(\d+)\."}
]

# --- Funções de Log e Auxiliares ---
log_file_path = None
def setup_logger(urn, logdir):
    global log_file_path
    log_file_name = urn.replace(";", "_") + ".log.jsonl"
    log_file_path = os.path.join(logdir, log_file_name)
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

def log_event(level, event, **kwargs):
    if not log_file_path:
        print(f"[LOG ERROR] Logger not initialized. Event: {event}", file=sys.stderr)
        return
    log_entry = {"timestamp": datetime.utcnow().isoformat() + "Z", "level": level, "event": event, **kwargs}
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def get_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def normalize_text(text):
    text = re.sub("-\n", "", text) # Remove hífens de fim de linha
    text = re.sub("[ \t]+", " ", text) # Multiplos espaços -> um espaço
    text = re.sub(" *\n *", "\n", text) # Espaços ao redor de newlines
    text = re.sub("\n{2,}", "\n", text) # Multiplos newlines -> um newline
    return text.strip()

def parse_recursivo_texto(text_block, parent_path, parent_level, data_publicacao, DEVICE_PATTERNS):
    children = []
    caput = text_block

    possible_child_patterns = [p for p in DEVICE_PATTERNS if p["level"] > parent_level]
    if not possible_child_patterns:
        return [], normalize_text(caput)

    all_matches = []
    for p_info in possible_child_patterns:
        for match in re.finditer(p_info["regex"], text_block):
            all_matches.append({"match": match, "p_info": p_info})
    
    all_matches.sort(key=lambda x: x["match"].start())

    if all_matches:
        highest_level_found = min(m["p_info"]["level"] for m in all_matches)
        top_level_matches = [m for m in all_matches if m["p_info"]["level"] == highest_level_found]
    else:
        return [], normalize_text(caput)

    caput = normalize_text(text_block[:top_level_matches[0]["match"].start()])

    for i, current in enumerate(top_level_matches):
        match = current["match"]
        p_info = current["p_info"]

        start_of_child_block = match.start()
        end_of_child_block = top_level_matches[i+1]["match"].start() if i + 1 < len(top_level_matches) else len(text_block)
        child_full_text = text_block[start_of_child_block:end_of_child_block]
        
        rotulo_raw = match.group(1).strip()
        ordem = i + 1

        caminho_estrutural = f"{parent_path}/{p_info['slug']}-{ordem}"
        log_event("DEBUG", f"FOUND_{p_info['tipo'].upper()}", path=caminho_estrutural)

        text_for_recursion = child_full_text[len(match.group(0)):]
        grandchildren, child_caput = parse_recursivo_texto(text_for_recursion, caminho_estrutural, p_info["level"], data_publicacao, DEVICE_PATTERNS)
        
        texto_normalizado = normalize_text(match.group(0) + " " + child_caput)

        dispositivo = {
            "rotulo": rotulo_raw, "tipo_dispositivo": p_info["tipo"], "caminho_estrutural": caminho_estrutural, "ordem": ordem,
            "versoes": [{"vigencia_inicio": data_publicacao, "vigencia_fim": None, "texto_normalizado": texto_normalizado, "hash_texto": get_sha256(texto_normalizado), "status_vigencia": "vigente", "origem_alteracao": None}],
            "filhos": grandchildren, "ancoras": None
        }
        children.append(dispositivo)

    return children, caput

def is_image_only_pdf(doc):
    for page in doc:
        if page.get_text():
            return False
    return True

# --- Parsers de Formato (Refatorados) ---
def parse_html(content, output_json, DEVICE_PATTERNS):
    log_event("INFO", "PARSE_HTML_START")
    soup = BeautifulSoup(content, 'html.parser')

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()

    body = soup.body
    if not body:
        log_event("ERROR", "NO_BODY_TAG_FOUND", message="Could not find the <body> tag in the HTML.")
        return output_json

    all_p_tags = body.find_all('p')

    article_starts = []
    for p in all_p_tags:
        if re.match(r'^\s*Art[\.\s]+?\d+[ºo]?', p.get_text().strip()):
            article_starts.append(p)

    if not article_starts:
        log_event("WARNING", "NO_ARTICLES_FOUND", message="Nenhum artigo encontrado no HTML usando a busca por tags <p>.")
        return output_json

    for i, start_node in enumerate(article_starts, 1):
        rotulo = start_node.get_text().strip()
        
        text_block_nodes = [start_node]
        current_node = start_node.find_next_sibling()
        while current_node:
            if current_node in article_starts:
                break
            text_block_nodes.append(current_node)
            current_node = current_node.find_next_sibling()
        
        texto_completo_artigo = "\n".join([n.get_text() for n in text_block_nodes])
        
        filhos, caput_artigo = parse_recursivo_texto(texto_completo_artigo, f"art-{i}", 0, output_json["ato_normativo"]["data_publicacao"], DEVICE_PATTERNS)

        dispositivo = {
            "rotulo": rotulo,
            "tipo_dispositivo": "artigo",
            "caminho_estrutural": f"art-{i}",
            "ordem": i,
            "versoes": [{"vigencia_inicio": output_json["ato_normativo"]["data_publicacao"], "vigencia_fim": None, "texto_normalizado": caput_artigo, "hash_texto": get_sha256(caput_artigo), "status_vigencia": "vigente", "origem_alteracao": None}],
            "filhos": filhos,
            "ancoras": None
        }
        output_json["dispositivos"].append(dispositivo)

    log_event("INFO", "PARSE_HTML_SUCCESS", article_count=len(article_starts))
    return output_json

def parse_pdf(content, output_json, DEVICE_PATTERNS):
    full_text = ""
    try:
        with fitz.open(stream=content, filetype="pdf") as doc:
            if not doc.is_pdf or doc.is_encrypted:
                log_event("ERROR", "PDF_INVALID", message="Arquivo não é um PDF válido ou está criptografado.")
                sys.exit(1)
            if is_image_only_pdf(doc):
                log_event("ERROR", "OCR_REQUIRED", message="PDF contém apenas imagens, OCR é necessário.")
                sys.exit(1)
            for page in doc:
                full_text += page.get_text("text") + "\n"
    except Exception as e:
        log_event("ERROR", "PDF_PROCESSING_FAILED", error=str(e))
        sys.exit(1)

    if not full_text.strip():
        log_event("ERROR", "EMPTY_TEXT", message="Nenhum texto extraído do PDF.")
        sys.exit(1)

    articles = re.split(r"(Art[\\.\s]+?\d+[ºo]?)", full_text)
    found_articles = []
    for i in range(1, len(articles), 2):
        if i + 1 < len(articles):
            found_articles.append((articles[i], articles[i+1]))

    if not found_articles:
        log_event("WARNING", "NO_ARTICLES_FOUND", message="Nenhum artigo encontrado no PDF.")
        return output_json

    for i, (rotulo, texto) in enumerate(found_articles, 1):
        texto_completo_artigo = rotulo + texto
        filhos, caput_artigo = parse_recursivo_texto(texto_completo_artigo, f"art-{i}", 0, output_json["ato_normativo"]["data_publicacao"], DEVICE_PATTERNS)

        dispositivo = {
            "rotulo": rotulo.strip(), "tipo_dispositivo": "artigo", "caminho_estrutural": f"art-{i}", "ordem": i,
            "versoes": [{"vigencia_inicio": output_json["ato_normativo"]["data_publicacao"], "vigencia_fim": None, "texto_normalizado": caput_artigo, "hash_texto": get_sha256(caput_artigo), "status_vigencia": "vigente", "origem_alteracao": None}],
            "filhos": filhos, "ancoras": None
        }
        output_json["dispositivos"].append(dispositivo)

    log_event("INFO", "PDF_PARSE_SUCCESS", article_count=len(found_articles))
    return output_json

# --- Função Principal de Orquestração (Refatorada) ---
def run_parser(config, outdir, logdir):
    urn = config['urn_lexml']
    setup_logger(urn, logdir)
    run_id = str(uuid4())
    log_event("INFO", "START_PARSE", config=config, run_id=run_id)

    file_content = None
    
    # Determina o caminho do arquivo fonte
    source_path = config.get("source_file_path") or config.get("key")
    if not source_path:
        log_event("ERROR", "NO_SOURCE_FOUND", message="Nem --source-file nem 'key' no manifesto foram fornecidos.")
        sys.exit(1)

    # Tenta ler de um caminho de arquivo local primeiro
    if os.path.exists(source_path):
        log_event("INFO", "SOURCE_RESOLVED", type="local", path=source_path)
        with open(source_path, 'rb') as f:
            file_content = f.read()
    # Fallback para MinIO
    else:
        bucket = config.get("bucket")
        if not bucket:
            log_event("ERROR", "MINIO_CONFIG_MISSING", message="Bucket não especificado para a chave MinIO.")
            sys.exit(1)
        
        log_event("INFO", "SOURCE_RESOLVED", type="minio", bucket=bucket, key=source_path)
        s3_client = boto3.client("s3", 
                                 endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"), 
                                 aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minio_admin"), 
                                 aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minio_password"))
        try:
            file_obj = s3_client.get_object(Bucket=bucket, Key=source_path)
            file_content = file_obj["Body"].read()
        except Exception as e:
            log_event("ERROR", "MINIO_DOWNLOAD_FAILED", error=str(e), bucket=bucket, key=source_path)
            sys.exit(1)

    # Prepara o JSON de saída
    output_json = {
        "ato_normativo": {
            "urn_lexml": urn,
            "tipo_ato": config.get("tipo_ato", "desconhecido"),
            "titulo": config.get("titulo", ""),
            "ementa": config.get("ementa", ""),
            "entidade_federativa": config.get("entidade_federativa", ""),
            "orgao_publicador": config.get("orgao_publicador", ""),
            "data_publicacao": config.get("data_publicacao", ""),
            "fonte_oficial": config.get("source_url", ""),
            "situacao_vigencia": "vigente"
        },
        "dispositivos": [],
        "auditoria": { "run_id": run_id, "parser_versao": PARSER_VERSION, "gerado_em": datetime.utcnow().isoformat() + "Z" }
    }

    file_ext = os.path.splitext(source_path)[1].lower()
    if file_ext == ".html":
        output_json = parse_html(file_content.decode("latin-1"), output_json, DEVICE_PATTERNS)
    elif file_ext == ".pdf":
        output_json = parse_pdf(file_content, output_json, DEVICE_PATTERNS)
    else:
        log_event("ERROR", "UNSUPPORTED_FILE_TYPE", extension=file_ext)
        sys.exit(1)

    # Escreve o arquivo de saída
    output_file_name = urn.replace(";", "_") + "_recursivo.json"
    output_file_path = os.path.join(outdir, output_file_name)
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=2)
    
    log_event("INFO", "WRITE_OUTPUT", path=output_file_path, device_count=len(output_json["dispositivos"]))
    log_event("INFO", "DONE")

# --- Bloco de Execução Principal (Refatorado) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parser LexML-Atlas v2.0")
    parser.add_argument("--manifest", help="Caminho para o arquivo de manifesto JSON da coleta.")
    parser.add_argument("--source-file", help="Caminho para o arquivo fonte local (sobrescreve o manifesto).")
    parser.add_argument("--outdir", default=os.getenv("PARSER_OUTDIR", "parser/output"), help="Diretório de saída para os arquivos JSON.")
    parser.add_argument("--logs", default=os.getenv("PARSER_LOGDIR", "parser/logs"), help="Diretório de saída para os arquivos de log.")
    
    args = parser.parse_args()

    if not args.manifest:
        print("Erro: O argumento --manifest é obrigatório.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.logs, exist_ok=True)
    
    with open(args.manifest, 'r') as f:
        config = json.load(f)
    
    # Permite sobrescrever o arquivo fonte do manifesto com um caminho local
    if args.source_file:
        config["source_file_path"] = args.source_file

    run_parser(config, args.outdir, args.logs)