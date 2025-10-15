"""
Este módulo implementa o coração do parser determinístico: uma Máquina de
Estados Finitos (FSM) para analisar a estrutura interna de um único artigo.

Ele identifica e aninha caput, parágrafos, incisos, alíneas e itens,
construindo uma árvore de dispositivos hierárquica.
"""
import re
from typing import Dict, List, Optional
from ..schemas import Artigo, Paragrafo, Inciso, Alinea, Item

# --- Regex para Identificação de Dispositivos ---
# Compiladas para eficiência e centralizadas para manutenção.

# Parágrafo: § 1º, § 10, § único.
PARAGRAFO_RE = re.compile(r"^\s*§\s*(\d+|[úÚ]nico)[\sºª]*\.?\s*(.*)", re.IGNORECASE)

# Inciso: I -, II -, XV - (numeração romana)
INCISO_RE = re.compile(r"^\s*(M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))\s*[-–—]\s*(.*)", re.IGNORECASE)

# Alínea: a), b)
ALINEA_RE = re.compile(r"^\s*([a-z])\)\s*(.*)", re.IGNORECASE)

# Item: 1., 2., 10.
ITEM_RE = re.compile(r"^\s*(\d+)\.\s*(.*)", re.IGNORECASE)


class ArticleParserFSM:
    """
    Uma Máquina de Estados Finitos para parsear o texto de um artigo.
    """
    def __init__(self, artigo_numero: str, artigo_rotulo: str, artigo_texto: str):
        self.artigo_numero = artigo_numero
        self.artigo_rotulo = artigo_rotulo
        self.texto_original = artigo_texto
        self.linhas = [line.strip() for line in artigo_texto.strip().split('\n') if line.strip()]
        
        # Estrutura de dados para o resultado
        self.resultado = {
            "numero": self.artigo_numero,
            "rotulo": self.artigo_rotulo,
            "caput": "",
            "paragrafos": [],
            "incisos": [],
        }
        self.confianca = 1.0
        self.erros = []

    def parse(self) -> Dict:
        """
        Executa o processo de parsing do artigo.
        """
        if not self.linhas:
            self.erros.append("Artigo sem conteúdo textual.")
            self.confianca = 0.0
            return self._build_final_structure()

        # O caput é a primeira linha (ou linhas) até o primeiro dispositivo.
        primeira_linha = self.linhas.pop(0)
        
        # Remove o rótulo do artigo do texto do caput
        caput_texto = primeira_linha.replace(self.artigo_rotulo, "", 1).strip()
        
        # Lógica simples para caput multi-linha
        while self.linhas and not self._is_dispositivo(self.linhas[0]):
            caput_texto += " " + self.linhas.pop(0)
        
        self.resultado["caput"] = caput_texto.strip()

        # Ponteiros para o estado atual da FSM
        current_paragrafo = None
        current_inciso = None
        current_alinea = None

        for linha in self.linhas:
            match_paragrafo = PARAGRAFO_RE.match(linha)
            match_inciso = INCISO_RE.match(linha)
            match_alinea = ALINEA_RE.match(linha)
            match_item = ITEM_RE.match(linha)

            if match_paragrafo:
                rotulo = f"§ {match_paragrafo.group(1)}"
                texto = match_paragrafo.group(2).strip()
                novo_paragrafo = {"rotulo": rotulo, "texto": texto, "incisos": [], "alineas": []}
                self.resultado["paragrafos"].append(novo_paragrafo)
                current_paragrafo = novo_paragrafo
                current_inciso = None
                current_alinea = None
            
            elif match_inciso:
                rotulo = match_inciso.group(1)
                texto = match_inciso.group(2).strip()
                novo_inciso = {"rotulo": rotulo, "texto": texto, "alineas": []}
                
                if current_paragrafo:
                    current_paragrafo["incisos"].append(novo_inciso)
                else:
                    self.resultado["incisos"].append(novo_inciso)
                
                current_inciso = novo_inciso
                current_alinea = None

            elif match_alinea:
                if not current_inciso:
                    self.erros.append(f"Alínea encontrada sem inciso pai: {linha}")
                    self.confianca -= 0.2
                    continue
                rotulo = match_alinea.group(1)
                texto = match_alinea.group(2).strip()
                nova_alinea = {"rotulo": rotulo, "texto": texto, "itens": []}
                current_inciso["alineas"].append(nova_alinea)
                current_alinea = nova_alinea

            elif match_item:
                if not current_alinea:
                    self.erros.append(f"Item encontrado sem alínea pai: {linha}")
                    self.confianca -= 0.2
                    continue
                rotulo = match_item.group(1)
                texto = match_item.group(2).strip()
                novo_item = {"rotulo": rotulo, "texto": texto}
                current_alinea["itens"].append(novo_item)
            
            else:
                # Concatena texto ao último dispositivo encontrado
                self._append_text_to_last_dispositivo(linha, current_paragrafo, current_inciso, current_alinea)

        return self._build_final_structure()

    def _is_dispositivo(self, linha: str) -> bool:
        """Verifica se uma linha marca o início de um novo dispositivo."""
        return bool(
            PARAGRAFO_RE.match(linha) or
            INCISO_RE.match(linha) or
            ALINEA_RE.match(linha) or
            ITEM_RE.match(linha)
        )

    def _append_text_to_last_dispositivo(self, texto: str, p: Dict, i: Dict, a: Dict):
        """Anexa texto de continuação ao dispositivo mais recente."""
        target = None
        if a and a.get("itens"):
            target = a["itens"][-1]
        elif a:
            target = a
        elif i and i.get("alineas"):
            target = i["alineas"][-1]
        elif i:
            target = i
        elif p and p.get("incisos"):
            target = p["incisos"][-1]
        elif p:
            target = p
        else:
            self.resultado["caput"] += " " + texto
            return
        
        if target:
            target["texto"] += " " + texto

    def _build_final_structure(self) -> Dict:
        """Constrói o objeto final usando os schemas Pydantic para validação."""
        try:
            # Converte dicionários em instâncias Pydantic
            artigo_obj = Artigo.parse_obj(self.resultado)
            return {
                "json": artigo_obj.dict(),
                "confianca": max(0, self.confianca),
                "erros": self.erros
            }
        except Exception as e:
            self.erros.append(f"Erro de validação Pydantic: {e}")
            return {
                "json": self.resultado, # Retorna o dict parcial
                "confianca": 0.0,
                "erros": self.erros
            }
