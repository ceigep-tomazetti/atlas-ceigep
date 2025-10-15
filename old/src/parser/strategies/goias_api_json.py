# src/parser/strategies/goias_api_json.py
import re
import logging
import hashlib
from src.preprocessor.main import ai_clean_text, ai_get_direct_children

# --- Funções Auxiliares ---

def _get_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _normalize_text(text):
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def _get_tipo_dispositivo(rotulo):
    rotulo = rotulo.lower()
    if rotulo.startswith('art'): return 'artigo'
    if rotulo.startswith('§') or rotulo.startswith('parágrafo'): return 'paragrafo'
    if re.match(r'^[ivxlcdm]+', rotulo): return 'inciso'
    if re.match(r'^[a-z]\)', rotulo): return 'alinea'
    if re.match(r'^\d+\.', rotulo): return 'item'
    return 'dispositivo'

# --- Lógica Recursiva ---

def _processar_dispositivo_recursivamente(texto_bruto, caminho_pai, data_publicacao):
    """
    Função recursiva que processa um dispositivo e seus filhos.
    """
    try:
        # 1. Chama IA para obter caput e filhos diretos
        data = ai_get_direct_children(texto_bruto)
        caput = _normalize_text(data.get("caput", texto_bruto))
        filhos_brutos = data.get("filhos", [])

        # 2. Processa os filhos recursivamente
        filhos_processados = []
        for i, filho in enumerate(filhos_brutos):
            ordem_filho = i + 1
            tipo_filho = _get_tipo_dispositivo(filho["rotulo"])
            slug = tipo_filho[:3]
            caminho_filho = f"{caminho_pai}/{slug}-{ordem_filho}"
            
            # Chamada recursiva
            filho_processado = _processar_dispositivo_recursivamente(
                filho["texto_completo"], caminho_filho, data_publicacao
            )
            
            # Adiciona metadados ao nó filho
            filho_processado.update({
                "rotulo": filho["rotulo"],
                "tipo_dispositivo": tipo_filho,
                "caminho_estrutural": caminho_filho,
                "ordem": ordem_filho,
            })
            filhos_processados.append(filho_processado)

        # 3. Monta o nó atual
        texto_normalizado = caput
        texto_original = texto_bruto
        
        dispositivo_atual = {
            "versoes": [{
                "vigencia_inicio": data_publicacao,
                "texto_original_parser": texto_original,
                "texto_normalizado": texto_normalizado,
                "hash_texto_normalizado": _get_sha256(texto_normalizado),
                "status_vigencia": "vigente"
            }],
            "filhos": filhos_processados
        }
        return dispositivo_atual

    except Exception as e:
        logging.error(f"Erro ao processar dispositivo em '{caminho_pai}': {e}")
        return {
            "versoes": [{"texto_normalizado": f"ERRO DE PARSING: {e}", "hash_texto_normalizado": ""}],
            "filhos": []
        }

# --- Estratégia Principal ---

def parse(manifest: dict):
    """
    Implementa a arquitetura "Processamento Hierárquico Recursivo".
    """
    metadata = manifest.get('metadados_fonte', {})
    full_text = metadata.get('conteudo_sem_formatacao')
    data_publicacao = manifest.get('data_publicacao')

    if not full_text:
        raise ValueError("O campo 'conteudo_sem_formatacao' está ausente.")

    # 1. Segmentar com LLM
    logging.info("Etapa 1: Segmentando corpo e anexos com IA...")
    cleaned_data = ai_clean_text(full_text)
    corpo_legislativo = cleaned_data.get("corpo_legislativo", "")
    anexos_brutos = cleaned_data.get("anexos", "")
    logging.info("Segmentação concluída.")

    # 2. Dividir corpo em artigos com Regex Ancorada
    logging.info("Etapa 2: Dividindo corpo legislativo em artigos...")
    matches = list(re.finditer(r'(?im)^Art\.?\s*\d+[ºo]?', corpo_legislativo))
    
    artigos = []
    for i, match in enumerate(matches):
        start_pos = match.start()
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(corpo_legislativo)
        artigos.append({
            "rotulo": match.group(0).strip(),
            "texto": corpo_legislativo[start_pos:end_pos].strip()
        })
    logging.info(f"{len(artigos)} artigos encontrados.")

    # 3. Iniciar recursão para cada artigo
    dispositivos_finais = []
    for i, artigo in enumerate(artigos):
        ordem = i + 1
        caminho_pai = f"art-{ordem}"
        logging.info(f"Etapa 3.{ordem}: Iniciando processamento recursivo para {artigo['rotulo']}...")
        
        # Remove o rótulo do texto antes de iniciar a recursão
        texto_sem_rotulo = artigo['texto'][len(artigo['rotulo']):].strip()
        
        dispositivo_processado = _processar_dispositivo_recursivamente(
            texto_sem_rotulo, caminho_pai, data_publicacao
        )
        
        dispositivo_processado.update({
            "rotulo": artigo["rotulo"],
            "tipo_dispositivo": "artigo",
            "caminho_estrutural": caminho_pai,
            "ordem": ordem,
        })
        dispositivos_finais.append(dispositivo_processado)
        logging.info(f"Processamento do {artigo['rotulo']} concluído.")

    # 4. Processar anexos
    anexos_finais = [{"titulo": "Anexo", "texto_bruto": anexos_brutos, "ordem": 1}] if anexos_brutos else []

    return {"dispositivos": dispositivos_finais, "anexos": anexos_finais}