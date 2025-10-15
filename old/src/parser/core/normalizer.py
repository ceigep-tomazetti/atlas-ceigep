"""
Este módulo contém funções para normalização e saneamento de texto bruto
de documentos legais. O objetivo é preparar o texto para as etapas de
segmentação e parsing, removendo ruídos comuns e padronizando o formato.
"""
import re

# Regex para encontrar linhas que contêm apenas números de página, possivelmente com espaços.
# Ex: " 12 ", "345"
PAGE_NUMBER_RE = re.compile(r"^\s*\d+\s*$", re.MULTILINE)

# Regex para encontrar múltiplos espaços ou tabulações dentro de uma linha.
MULTIPLE_SPACES_RE = re.compile(r"[ \t]+")

def normalize_text(texto_bruto: str) -> str:
    """
    Executa uma série de passos de normalização em um texto bruto.

    - Converte todas as quebras de linha para o padrão Unix (\n).
    - Remove linhas que contêm apenas números de página.
    - Colapsa múltiplos espaços em um único espaço.
    - Garante que o texto termine com uma única quebra de linha.

    Args:
        texto_bruto: O texto extraído da fonte.

    Returns:
        O texto normalizado e pronto para o parsing.
    """
    # 1. Converte \r\n e \r para \n
    texto = texto_bruto.replace('\r\n', '\n').replace('\r', '\n')

    # 2. Remove linhas com apenas números de página
    texto = PAGE_NUMBER_RE.sub('', texto)

    # 3. Colapsa espaços múltiplos e normaliza quebras de linha
    linhas = texto.split('\n')
    linhas_normalizadas = []
    for linha in linhas:
        # Colapsa espaços dentro da linha
        linha_sem_espacos_multiplos = MULTIPLE_SPACES_RE.sub(' ', linha).strip()
        if linha_sem_espacos_multiplos: # Adiciona apenas se a linha não ficar vazia
            linhas_normalizadas.append(linha_sem_espacos_multiplos)

    # Junta as linhas de volta, garantindo uma quebra de linha entre elas
    texto_normalizado = '\n'.join(linhas_normalizadas)

    # 4. Garante que o texto termine com uma única quebra de linha
    if texto_normalizado:
        return texto_normalizado + '\n'
    
    return ""
