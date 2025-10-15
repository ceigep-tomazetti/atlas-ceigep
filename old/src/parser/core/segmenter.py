"""
Este módulo implementa a lógica de segmentação de um documento legal em
seus componentes principais, como "corpo" e "anexos".

Ele contém a implementação do fallback via regex, a ser usado quando a
abordagem primária (LLM) não for conclusiva.
"""
import re
from typing import List, Dict, Optional

# Regex robusta para encontrar o início de um anexo.
# Captura "ANEXO", "ANEXO I", "ANEXO II", "ANEXO ÚNICO", "APÊNDICE", etc.
# - (?mi): case-insensitive e multiline
# - ^: início da linha
# - \b: fronteira de palavra, para não capturar "ANEXOS" no meio de uma frase.
ANEXO_RE = re.compile(r"(?mi)^(ANEXO(?:\s+ÚNICO|\s+[IVXLCDM]+)?|APÊNDICE)\b")

def segment_by_regex(texto_normalizado: str) -> Optional[List[Dict]]:
    """
    Segmenta o texto em "corpo" e "anexo(s)" usando uma expressão regular.

    Esta função serve como um fallback para a segmentação via LLM. Ela procura
    pela primeira ocorrência de um marcador de anexo (ex: "ANEXO I") e divide
    o texto nesse ponto.

    Args:
        texto_normalizado: O texto completo do documento, já normalizado.

    Returns:
        Uma lista de dicionários, cada um representando um bloco de texto
        (ex: {'tipo': 'corpo', 'start': 0, 'end': 12345}), ou None se o texto
        for vazio.
    """
    if not texto_normalizado:
        return None

    match = ANEXO_RE.search(texto_normalizado)

    if match:
        # Encontrou um anexo. O corpo vai do início até o começo do match.
        ponto_de_corte = match.start()
        
        # Para evitar cortar por um falso positivo no início do documento
        if ponto_de_corte == 0:
             # Se o anexo está na primeira linha, não há corpo. Considera tudo anexo.
             # (Caso de uso raro, mas é uma salvaguarda)
             # Na prática, vamos assumir que sempre há um corpo.
             # Se o anexo é a primeira coisa, o corpo será vazio.
             pass

        corpo = {
            "tipo": "corpo",
            "start": 0,
            "end": ponto_de_corte
        }
        
        # O primeiro anexo começa no ponto de corte e vai até o fim.
        # A lógica não tenta encontrar múltiplos anexos, apenas o primeiro.
        # O restante do texto é considerado um único bloco de anexo.
        anexo = {
            "tipo": "anexo",
            "start": ponto_de_corte,
            "end": len(texto_normalizado),
            "rotulo": match.group(0).strip()
        }
        
        # Retorna os blocos, ignorando o corpo se ele for vazio
        return [corpo, anexo] if corpo["end"] > corpo["start"] else [anexo]

    else:
        # Nenhum anexo encontrado, todo o texto é considerado corpo.
        return [{
            "tipo": "corpo",
            "start": 0,
            "end": len(texto_normalizado)
        }]
