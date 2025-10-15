"""
Este módulo é responsável por dividir o corpo de um texto legal em seus
componentes fundamentais: o cabeçalho (ementa, preâmbulo) e uma lista
de artigos.

A divisão é feita de forma determinística usando uma expressão regular
confiável que identifica o início de cada artigo.
"""
import re
from typing import List, Dict, Tuple

# Regex para encontrar o início de um artigo.
# - (?im): case-insensitive e multiline.
# - ^: início da linha.
# - (?=...): lookahead positivo, garante que o padrão exista mas não o consome.
#   Isso é crucial para que o re.split() (se usado) ou o finditer() funcionem corretamente.
# - Art(?:igo)?: Corresponde a "Art" ou "Artigo".
# - \.?: Corresponde ao ponto literal opcional.
# - \s*: Espaços em branco.
# - \d+: Um ou mais dígitos.
# - [ºoª]?: Caracteres ordinais opcionais.
ART_RE = re.compile(r"(?im)^(Art(?:igo)?\.?\s*\d+[ºoª]?)")

# Regex aprimorada para extrair o rótulo e o número do artigo.
ART_EXTRACT_RE = re.compile(r"(?i)(Art(?:igo)?\.?)\s*(\d+)([ºoª]?)")

def _normalize_article_number(num_str: str) -> str:
    """Remove zeros à esquerda para consistência."""
    return str(int(num_str))

def split_body_into_articles(corpo_texto: str) -> Dict:
    """
    Divide o texto do corpo de um ato normativo em cabeçalho e artigos.

    Args:
        corpo_texto: A string contendo o corpo completo do ato.

    Returns:
        Um dicionário contendo os spans do cabeçalho e de cada artigo.
        Ex: {
            'header_span': {'start': 0, 'end': 150},
            'article_spans': [{'start': 150, 'end': 500, 'rotulo': 'Art. 1º', 'numero': '1'}, ...]
        }
    """
    matches = list(ART_RE.finditer(corpo_texto))
    
    if not matches:
        # Se nenhum artigo for encontrado, todo o corpo é considerado cabeçalho.
        return {
            'header_span': {'start': 0, 'end': len(corpo_texto)},
            'article_spans': []
        }

    # O cabeçalho é o texto do início até o começo do primeiro artigo.
    first_match_start = matches[0].start()
    header_span = {'start': 0, 'end': first_match_start}
    
    article_spans = []
    for i, match in enumerate(matches):
        start = match.start()
        # O fim de um artigo é o começo do próximo, ou o fim do texto.
        end = matches[i + 1].start() if i + 1 < len(matches) else len(corpo_texto)
        
        # O rótulo é o texto exato encontrado pelo match.
        rotulo = match.group(1).strip()
        
        # Extrai o número para fins de ordenação e identificação.
        num_match = ART_EXTRACT_RE.search(rotulo)
        numero = _normalize_article_number(num_match.group(2)) if num_match else "N/A"

        article_spans.append({
            'start': start,
            'end': end,
            'rotulo': rotulo,
            'numero': numero
        })
        
    return {
        'header_span': header_span,
        'article_spans': article_spans
    }
