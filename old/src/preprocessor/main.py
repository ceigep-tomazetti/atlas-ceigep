# src/preprocessor/main.py
import os
import json
import logging
import hashlib
import re
import time
from typing import List, Dict, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuração ---
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env')))

GEMINI_API_KEYS = [key.strip() for key in os.getenv("GEMINI_API_KEYS", "").split(',') if key.strip()]
CANDIDATE_MODELS = ["models/gemini-2.5-flash", "models/gemini-2.5-pro"] # Prioriza o Flash por velocidade e custo

# --- Novas Funções para Arquitetura "Segmentar e Conquistar" ---

def ai_segment_document(texto_normalizado: str) -> Optional[List[Dict]]:
    """
    Usa um LLM para identificar o ponto de corte entre o corpo e os anexos,
    focando em encontrar o "fim do corpo legal" com uma estratégia de janela deslizante.

    Args:
        texto_normalizado: O texto completo e limpo do documento.

    Returns:
        Uma lista de dicionários de segmento, ou None para acionar o fallback.
    """
    if not GEMINI_API_KEYS:
        logging.error("Nenhuma chave de API do Gemini encontrada no .env.")
        raise ValueError("Nenhuma chave de API do Gemini encontrada.")

    chunk_size = 3000
    max_attempts = 5  # Analisará até os últimos 15k caracteres

    for i in range(max_attempts):
        end_pos = len(texto_normalizado) - (i * chunk_size)
        start_pos = max(0, end_pos - chunk_size)
        
        if start_pos >= end_pos: break # Evita loops infinitos em textos curtos

        texto_para_analise = texto_normalizado[start_pos:end_pos]
        logging.info(f"Tentativa {i+1}/{max_attempts}: Analisando trecho de {start_pos} a {end_pos}.")

        prompt = f"""
        Você é um especialista em análise de documentos jurídicos. Sua tarefa é encontrar a **última linha do corpo principal** do texto legal fornecido.

        O "corpo principal" termina com o **fecho**, que inclui data, local e assinaturas (ex: "Publique-se.", "GABINETE DO PREFEITO", "JOÃO DA SILVA"). Ignore qualquer conteúdo que seja claramente um anexo, tabela ou apêndice.

        Retorne um objeto JSON com a chave "ultima_linha_corpo".
        - Se você encontrar o fecho, o valor deve ser a string exata da última linha (ex: "MARCONI FERREIRA PERILLO JÚNIOR").
        - Se este trecho parecer ser **inteiramente parte de um anexo** (ex: apenas dados de uma tabela), retorne o valor `null`.

        **Texto para Análise:**
        ---
        {texto_para_analise}
        ---
        """

        generation_config = {"response_mime_type": "application/json", "temperature": 0.0}

        for model_name in CANDIDATE_MODELS:
            for j, api_key in enumerate(GEMINI_API_KEYS):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name, generation_config=generation_config)
                    response = model.generate_content(prompt, request_options={'timeout': 60})
                    
                    result = json.loads(response.text)
                    ultima_linha = result.get("ultima_linha_corpo")

                    if not ultima_linha:
                        # IA acha que este trecho é um anexo, vamos para o próximo.
                        logging.info(f"IA não encontrou fecho no trecho. Movendo janela para cima.")
                        break # Sai do loop de chaves/modelos para a próxima janela

                    # Encontramos uma candidata. Agora, validamos no texto completo.
                    # Usamos rfind para pegar a última ocorrência, mais provável de ser a correta.
                    pos_linha = texto_normalizado.rfind(ultima_linha)

                    if pos_linha != -1:
                        ponto_de_corte = pos_linha + len(ultima_linha)
                        
                        # Heurística: se o corte está muito perto do fim, provavelmente não há anexo.
                        if len(texto_normalizado) - ponto_de_corte < 100:
                             logging.info("Fecho encontrado no final do documento. Assumindo ausência de anexos.")
                             return [{"tipo": "corpo", "start": 0, "end": len(texto_normalizado)}]

                        logging.info(f"SUCESSO: Fecho encontrado. Corpo termina em '{ultima_linha}'.")
                        corpo = {"tipo": "corpo", "start": 0, "end": ponto_de_corte}
                        anexo = {"tipo": "anexo", "start": ponto_de_corte, "end": len(texto_normalizado)}
                        return [corpo, anexo]
                    else:
                        logging.warning(f"IA retornou linha '{ultima_linha}' que não foi encontrada. Movendo janela.")
                        break # Sai do loop de chaves/modelos

                except Exception as e:
                    logging.warning(f"Falha na segmentação com chave #{j+1} para modelo '{model_name}': {e}")
                    continue
            
            # Se chegamos aqui, ou a IA retornou null ou a linha não foi encontrada.
            # Em ambos os casos, quebramos para a próxima iteração da janela.
            break

    logging.warning("IA não encontrou o fim do corpo legal. Acionando fallback de regex.")
    return None


def ai_parse_article_structure(texto_artigo: str) -> Optional[Dict]:
    """
    (Fallback) Usa um LLM para estruturar o conteúdo de um único artigo.

    Esta função é um fallback para a máquina de estados (FSM), usada apenas
    quando a confiança da análise determinística é baixa.

    Args:
        texto_artigo: O texto bruto de um único artigo.

    Returns:
        Um dicionário com a estrutura do artigo (caput, parágrafos, etc.),
        ou None em caso de falha.
    """
    # TODO: Implementar a lógica de chamada à IA conforme o plano.
    # O prompt instruirá o modelo a receber o texto de 1 artigo e retornar
    # a estrutura JSON aninhada (caput, paragrafos, incisos, etc.).
    logging.info(f"Executando micro-LLM para artigo de {len(texto_artigo)} caracteres.")
    return None


# --- Funções Legadas (a serem reavaliadas/removidas) ---

def ai_clean_text(texto_bruto: str) -> dict:
    """
    Usa um LLM para separar o texto bruto em 'corpo_legislativo', 'fecho' e 'anexos'.
    """
    if not GEMINI_API_KEYS:
        raise ValueError("Nenhuma chave de API do Gemini encontrada no arquivo .env.")

    prompt = f"""
    Você é um especialista em análise de documentos jurídicos. Sua tarefa é segmentar o texto bruto de um ato normativo em três partes: "corpo_legislativo", "fecho" e "anexos".

    - "corpo_legislativo": Contém o preâmbulo e todos os artigos, parágrafos, incisos, etc. Termina antes da data e assinatura.
    - "fecho": Contém a linha de data/local (ex: "GABINETE DO SECRETÁRIO...") e a assinatura.
    - "anexos": Contém todo o conteúdo que aparece após o fecho, como "QUADRO 1", "ANEXO II", etc.

    Analise o texto abaixo e retorne um objeto JSON com essas três chaves. Se uma seção não existir, retorne uma string vazia para ela.

    **Texto Bruto:**
    ---
    {texto_bruto}
    ---

    **JSON de Saída:**
    """

    generation_config = {"response_mime_type": "application/json"}

    for i, api_key in enumerate(GEMINI_API_KEYS):
        logging.info(f"Tentando chamada à API de limpeza com a chave #{i + 1}...")
        try:
            genai.configure(api_key=api_key)
            
            for model_name in CANDIDATE_MODELS:
                logging.info(f"Tentando com o modelo: {model_name}...")
                try:
                    model = genai.GenerativeModel(model_name, generation_config=generation_config)
                    response = model.generate_content(prompt)
                    
                    json_response = json.loads(response.text)
                    logging.info(f"Limpeza com IA bem-sucedida usando a chave #{i + 1} e o modelo '{model_name}'.")
                    return json_response

                except Exception as model_error:
                    logging.warning(f"Falha com o modelo '{model_name}': {model_error}")
                    continue

        except Exception as key_error:
            logging.warning(f"Falha ao usar a chave #{i + 1}: {key_error}")
            if "quota" in str(key_error).lower() or "resource has been exhausted" in str(key_error).lower():
                continue
            else:
                raise key_error

    raise Exception("Todas as chaves de API e modelos candidatos para limpeza falharam.")

def _add_hashes_recursively(dispositivos: list):
    """
    Percorre recursivamente a lista de dispositivos e adiciona o hash SHA256
    para cada versão textual.
    """
    for dispositivo in dispositivos:
        if 'versoes' in dispositivo and isinstance(dispositivo['versoes'], list):
            for versao in dispositivo['versoes']:
                texto = versao.get("texto_normalizado", "")
                versao["hash_texto_normalizado"] = hashlib.sha256(texto.encode('utf-8')).hexdigest()
        
        if 'filhos' in dispositivo and isinstance(dispositivo['filhos'], list):
            _add_hashes_recursively(dispositivo['filhos'])

def ai_get_direct_children(texto_dispositivo: str) -> dict:
    """
    Usa um LLM para identificar o caput e os filhos diretos de um dispositivo.
    Retorna o caput e uma lista de textos brutos para cada filho.
    """
    logging.info(f"Buscando filhos diretos em texto de {len(texto_dispositivo)} caracteres.")
    if not GEMINI_API_KEYS:
        raise ValueError("Nenhuma chave de API do Gemini encontrada.")

    prompt = f"""
    Você é um especialista em análise de documentos jurídicos. Sua tarefa é simples e focada:
    Analise o texto abaixo e separe-o em duas partes: o "caput" e uma lista de "filhos".

    1.  **caput**: É o texto principal do dispositivo, antes de qualquer parágrafo, inciso, alínea ou item.
    2.  **filhos**: É uma lista de objetos. Cada objeto deve ter duas chaves: "rotulo" (ex: "§ 1º", "I", "a)") e "texto_completo" (o texto inteiro daquele filho, incluindo seus próprios sub-itens).

    **NÃO aninhe a estrutura.** Apenas identifique os filhos diretos.

    **Exemplo de Saída:**
    ```json
    {{
      "caput": "Este é o texto do caput do artigo.",
      "filhos": [
        {{ 
          "rotulo": "§ 1º", 
          "texto_completo": "§ 1º Texto completo do parágrafo, incluindo seus incisos e alíneas que podem estar dentro dele."
        }},
        {{ 
          "rotulo": "§ 2º", 
          "texto_completo": "§ 2º Texto completo do segundo parágrafo."
        }}
      ]
    }}
    ```

    **Texto para Análise:**
    ---
    {texto_dispositivo}
    ---

    **JSON de Saída:**
    """
    generation_config = {"response_mime_type": "application/json", "temperature": 0.0}

    for model_name in CANDIDATE_MODELS:
        logging.info(f"Tentando com o modelo prioritário: {model_name}...")
        for i, api_key in enumerate(GEMINI_API_KEYS):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_name, generation_config=generation_config)
                response = model.generate_content(prompt, request_options={'timeout': 180})
                return json.loads(response.text)
            except Exception as e:
                logging.warning(f"Falha com a chave #{i + 1} para o modelo '{model_name}': {e}")
                error_text = str(e)
                if "quota" in error_text.lower() or "429" in error_text:
                    match = re.search(r'seconds: (\d+)', error_text)
                    if match:
                        wait_time = int(match.group(1)) + 1
                        logging.info(f"Limite de taxa. Aguardando {wait_time}s...")
                        time.sleep(wait_time)
                continue
        logging.warning(f"Modelo '{model_name}' falhou. Tentando próximo.")
    raise Exception("Falha ao obter filhos diretos da IA.")

def ai_extract_relations(texto_dispositivo: str) -> list:
    """
    Usa um LLM para extrair relações jurídicas de um trecho de texto.
    """
    if not GEMINI_API_KEYS:
        raise ValueError("Nenhuma chave de API do Gemini encontrada no arquivo .env.")

    prompt = f"""
    Você é um especialista em análise de documentos jurídicos brasileiros. Sua tarefa é encontrar todas as menções a outros atos normativos no texto fornecido e extrair as informações como uma lista de objetos JSON.

    **Regras:**
    1.  Sua saída DEVE ser uma lista de objetos JSON, ou uma lista vazia `[]` se nenhuma menção for encontrada.
    2.  Extraia os seguintes tipos de relação: 'ALTERA', 'REVOGA', 'REGULAMENTA', 'REMETE_A'.
    3.  Para cada menção, extraia o tipo de ato, o número e o ano para construir a URN de destino.
    4.  O formato da URN de destino deve ser: 'br;[esfera];[tipo_ato];[ano];[numero]'. Use 'br;go;estadual' para a esfera, a menos que o texto indique claramente 'federal'.

    **Exemplo de Saída:**
    ```json
    [
      {{
        "tipo_relacao": "REVOGA",
        "texto_encontrado": "revogado pela Lei nº 123, de 2022",
        "urn_destino_tipo_ato": "lei",
        "urn_destino_numero": "123",
        "urn_destino_ano": "2022"
      }},
      {{
        "tipo_relacao": "ALTERA",
        "texto_encontrado": "redação dada pela Emenda Constitucional nº 45, de 2004",
        "urn_destino_tipo_ato": "emenda.constitucional",
        "urn_destino_numero": "45",
        "urn_destino_ano": "2004"
      }}
    ]
    ```

    **Texto para Análise:**
    ---
    {texto_dispositivo}
    ---

    **JSON de Saída:**
    """

    generation_config = {
        "response_mime_type": "application/json",
        "temperature": 0.0
    }

    # Lógica de fallback: primeiro tenta o modelo Pro com todas as chaves, depois o Flash.
    for model_name in CANDIDATE_MODELS:
        logging.info(f"Tentando extração de relações com o modelo prioritário: {model_name}...")
        for i, api_key in enumerate(GEMINI_API_KEYS):
            api_key_short = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else api_key
            logging.info(f"Tentando com a chave #{i + 1} ({api_key_short})...")
            
            try:
                genai.configure(api_key=api_key)
                
                model = genai.GenerativeModel(model_name, generation_config=generation_config)
                response = model.generate_content(prompt, request_options={'timeout': 120})
                
                json_response = json.loads(response.text)
                logging.info(f"Extração de relações com IA bem-sucedida usando o modelo '{model_name}'.")
                return json_response

            except Exception as e:
                logging.warning(f"Falha na extração de relações com a chave #{i + 1} para o modelo '{model_name}': {e}")
                
                # Lógica de espera inteligente para erros de cota
                error_text = str(e)
                if "quota" in error_text.lower() or "429" in error_text:
                    match = re.search(r'retry_delay {\s*seconds: (\d+)\s*}', error_text)
                    if match:
                        wait_time = int(match.group(1)) + 1
                        logging.info(f"Limite de taxa atingido. Aguardando {wait_time} segundos conforme solicitado pela API...")
                        time.sleep(wait_time)

                continue
        
        logging.warning(f"Modelo '{model_name}' falhou com todas as chaves de API. Tentando próximo modelo.")

    raise Exception("Todas as chaves de API e modelos candidatos para extração de relações falharam.")
