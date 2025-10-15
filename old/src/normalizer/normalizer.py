
import json
import os
import re
import argparse
import hashlib
from datetime import datetime
import sys

# --- Configuração ---
TRIGGER_WORDS = [
    'Redação dada', 'Incluído', 'Revogado', 'Vide', 'Regulamenta',
    'Acrescentado', 'Alterado', 'Renumerado', 'com redação', 'Dispositivo vetado',
    'Vigência', 'Produção de efeito'
]
PROTECTED_PATTERNS = [
    r"^\s*[IVXLCDM]+\s*$", # Apenas um inciso, ex: (I)
    r"^\s*[a-z]\s*$",      # Apenas uma alínea, ex: (a)
    r"^\s*\d+\s*$",       # Apenas um item, ex: (1)
    r"^\s*§\s*\d+",       # Apenas um parágrafo, ex: (§ 1º)
]

# --- Configuração de Log ---
log_file_path = None
def setup_logger(urn, logdir):
    global log_file_path
    log_file_name = f"{urn}_normalizer.log.jsonl"
    log_file_path = os.path.join(logdir, log_file_name)
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

def log_event(level, event, **kwargs):
    if not log_file_path:
        print(f"[LOG ERROR] Logger not initialized for normalizer. Event: {event}", file=sys.stderr)
        return
    log_entry = {"timestamp": datetime.utcnow().isoformat() + "Z", "level": level, "event": event, **kwargs}
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

# --- Funções Auxiliares ---
def get_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# --- Lógica de Normalização ---

def normalize_device_text(dispositivo):
    """Normaliza recursivamente o texto de um dispositivo e seus filhos."""
    if "versoes" in dispositivo and dispositivo["versoes"]:
        for i, versao in enumerate(dispositivo["versoes"]):
            original_text = versao.get("texto_normalizado", "")
            
            versao["texto_original_parser"] = original_text
            
            cleaned_text = original_text
            removed_chars = 0
            regras_aplicadas = []

            def remove_parenthetical(match):
                nonlocal removed_chars
                content = match.group(1)
                has_trigger = any(trigger.lower() in content.lower() for trigger in TRIGGER_WORDS)
                is_protected = any(re.fullmatch(pattern, content) for pattern in PROTECTED_PATTERNS)
                
                if has_trigger and not is_protected:
                    removed_chars += len(match.group(0))
                    if "regra_1_parenteses" not in regras_aplicadas:
                        regras_aplicadas.append("regra_1_parenteses")
                    return ""
                else:
                    return match.group(0)

            cleaned_text = re.sub(r'\(([^)]*?)\)', remove_parenthetical, cleaned_text)
            cleaned_text = " ".join(cleaned_text.split()).strip()

            versao["texto_normalizado"] = cleaned_text
            versao["hash_texto_normalizado"] = get_sha256(cleaned_text)
            versao["normalizacao"] = {
                "regras_aplicadas": regras_aplicadas,
                "removido_total_chars": removed_chars
            }

    if "filhos" in dispositivo and dispositivo["filhos"]:
        for filho in dispositivo["filhos"]:
            normalize_device_text(filho)

# --- Função Principal ---
def main(input_path, outdir="src/normalizer/output", logdir="src/normalizer/logs"):
    """Função principal que orquestra o processo de normalização."""
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(logdir, exist_ok=True)

    urn_base = os.path.basename(input_path).replace("_recursivo.json", "")
    setup_logger(urn_base, logdir)

    log_event("INFO", "START_NORMALIZATION", input_file=input_path)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        log_event("ERROR", "FILE_NOT_FOUND", path=input_path)
        sys.exit(1)
    except json.JSONDecodeError as e:
        log_event("ERROR", "JSON_DECODE_ERROR", error=str(e))
        sys.exit(1)

    if "dispositivos" in data:
        for dispositivo in data["dispositivos"]:
            normalize_device_text(dispositivo)

    # Salvar o JSON normalizado
    output_path = os.path.join(outdir, f"{urn_base}_normalizado.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log_event("INFO", "NORMALIZED_FILE_SAVED", path=output_path)
    print(f"Arquivo normalizado salvo em: {output_path}")

    # A geração de diff foi removida para simplificar
    log_event("INFO", "END_NORMALIZATION")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalizador de JSON LexML-Atlas.")
    parser.add_argument("--input", required=True, help="Caminho para o arquivo JSON de entrada do parser.")
    parser.add_argument("--outdir", default="src/normalizer/output", help="Diretório de saída para os arquivos normalizados.")
    parser.add_argument("--logdir", default="src/normalizer/logs", help="Diretório para salvar os logs.")
    args = parser.parse_args()
    main(args.input, args.outdir, args.logdir)
