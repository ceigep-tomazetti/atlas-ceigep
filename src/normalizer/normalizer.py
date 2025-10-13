
import json
import os
import re
import argparse
import hashlib
from datetime import datetime

# --- Configuração ---
LOG_DIR = "normalizer/logs"
OUTPUT_DIR = "normalizer/output"
PARSER_VERSION = "1.0.0-normalizer"

# Regra #1: Palavras-gatilho para remoção de parênteses
TRIGGER_WORDS = [
    'Redação dada', 'Incluído', 'Revogado', 'Vide', 'Regulamenta',
    'Acrescentado', 'Alterado', 'Renumerado', 'com redação', 'Dispositivo vetado',
    'Vigência', 'Produção de efeito'
]
# Padrões estruturais a serem preservados
PROTECTED_PATTERNS = [
    r"^\s*[IVXLCDM]+\s*$", # Apenas um inciso, ex: (I)
    r"^\s*[a-z]\s*$",      # Apenas uma alínea, ex: (a)
    r"^\s*\d+\s*$",       # Apenas um item, ex: (1)
    r"^\s*§\s*\d+",       # Apenas um parágrafo, ex: (§ 1º)
]

# --- Funções Auxiliares ---
def get_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def log_event(log_file, data):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

# --- Lógica de Normalização ---

def normalize_device_text(dispositivo, log_file):
    if "versoes" in dispositivo and dispositivo["versoes"]:
        for i, versao in enumerate(dispositivo["versoes"]):
            original_text = versao.get("texto_normalizado", "")
            
            # Preserva o texto original do parser
            versao["texto_original_parser"] = original_text
            
            cleaned_text = original_text
            removed_chars = 0
            regras_aplicadas = []

            # --- Aplicação da Regra #1 ---
            # Usa uma função para substituir, permitindo a lógica de verificação
            def remove_parenthetical(match):
                nonlocal removed_chars
                content = match.group(1)
                # Verifica se alguma palavra-gatilho está presente
                has_trigger = any(trigger.lower() in content.lower() for trigger in TRIGGER_WORDS)
                # Verifica se o conteúdo NÃO é um padrão estrutural protegido
                is_protected = any(re.fullmatch(pattern, content) for pattern in PROTECTED_PATTERNS)
                
                if has_trigger and not is_protected:
                    removed_chars += len(match.group(0))
                    if "regra_1_parenteses" not in regras_aplicadas:
                        regras_aplicadas.append("regra_1_parenteses")
                    return "" # Remove a expressão inteira
                else:
                    return match.group(0) # Mantém a expressão

            # Regex para encontrar todo tipo de parênteses
            cleaned_text = re.sub(r'\(([^)]*?)\)', remove_parenthetical, cleaned_text)
            cleaned_text = normalize_text(cleaned_text)

            # Atualiza o dispositivo
            versao["texto_normalizado"] = cleaned_text
            versao["hash_texto_normalizado"] = get_sha256(cleaned_text)
            versao["normalizacao"] = {
                "regras_aplicadas": regras_aplicadas,
                "removido_total_chars": removed_chars
            }

            # Log do processamento deste dispositivo
            log_event(log_file, {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "caminho_estrutural": dispositivo.get("caminho_estrutural"),
                "chars_antes": len(original_text),
                "chars_depois": len(cleaned_text),
                "removido": len(original_text) - len(cleaned_text),
                "regras_aplicadas": regras_aplicadas
            })

    # Processa recursivamente os filhos
    if "filhos" in dispositivo and dispositivo["filhos"]:
        for filho in dispositivo["filhos"]:
            normalize_device_text(filho, log_file)

def normalize_text(text):
    # Colapsa múltiplos espaços e remove espaços no início/fim
    return " ".join(text.split()).strip()

# --- Função Principal ---
def main(input_path):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    base_name = os.path.basename(input_path).replace("_recursivo.json", "").replace("_art5_recursivo.json", "")
    log_file = os.path.join(LOG_DIR, f"{base_name}_normalizer.log.jsonl")
    output_file = os.path.join(OUTPUT_DIR, f"{base_name}_normalizado.json")
    diff_file = os.path.join(OUTPUT_DIR, f"{base_name}_diff.md")

    # Limpa log anterior
    if os.path.exists(log_file):
        os.remove(log_file)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Itera sobre a árvore de dispositivos e aplica a normalização
    for dispositivo in data["dispositivos"]:
        normalize_device_text(dispositivo, log_file)
    
    # Atualiza a versão do parser no bloco de auditoria
    data["auditoria"]["parser_versao"] = PARSER_VERSION
    data["auditoria"]["normalizado_em"] = datetime.utcnow().isoformat() + "Z"

    # Salva o JSON normalizado
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Arquivo normalizado salvo em: {output_file}")

    # --- Gera Relatório de Diff ---
    diff_report = "# Relatório de Normalização (Antes e Depois)\n\n"
    # Amostra: Art. 5, Inciso XI, Inciso XII
    art5 = next((d for d in data["dispositivos"] if d["caminho_estrutural"] == "art-5"), None)
    if art5:
        diff_report += "## Art. 5º (caput)\n"
        diff_report += "**Antes:**\n```\n" + art5["versoes"][0]["texto_original_parser"] + "\n```\n"
        diff_report += "**Depois:**\n```\n" + art5["versoes"][0]["texto_normalizado"] + "\n```\n\n"

        inc_xi = next((f for f in art5["filhos"] if f["caminho_estrutural"] == "art-5/inc-11"), None)
        if inc_xi:
            diff_report += "## Art. 5º, Inciso XI\n"
            diff_report += "**Antes:**\n```\n" + inc_xi["versoes"][0]["texto_original_parser"] + "\n```\n"
            diff_report += "**Depois:**\n```\n" + inc_xi["versoes"][0]["texto_normalizado"] + "\n```\n\n"

        inc_xii = next((f for f in art5["filhos"] if f["caminho_estrutural"] == "art-5/inc-12"), None)
        if inc_xii:
            diff_report += "## Art. 5º, Inciso XII\n"
            diff_report += "**Antes:**\n```\n" + inc_xii["versoes"][0]["texto_original_parser"] + "\n```\n"
            diff_report += "**Depois:**\n```\n" + inc_xii["versoes"][0]["texto_normalizado"] + "\n```\n\n"

    with open(diff_file, "w", encoding="utf-8") as f:
        f.write(diff_report)
    print(f"Relatório de diferenças salvo em: {diff_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalizador de textos de dispositivos legais.")
    parser.add_argument("--input", required=True, help="Caminho para o arquivo JSON de entrada (saída do parser).")
    args = parser.parse_args()
    main(args.input)
