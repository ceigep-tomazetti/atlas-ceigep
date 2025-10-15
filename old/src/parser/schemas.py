"""
Este módulo define os schemas de dados (contratos de I/O) para o pipeline de parsing,
utilizando Pydantic para validação e estruturação.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

# --- Estruturas Aninhadas (Dispositivos) ---

class Item(BaseModel):
    """Representa um item dentro de uma alínea."""
    tipo: Literal["item"] = "item"
    rotulo: str
    texto: str

class Alinea(BaseModel):
    """Representa uma alínea dentro de um inciso."""
    tipo: Literal["alinea"] = "alinea"
    rotulo: str
    texto: str
    itens: List[Item] = Field(default_factory=list)

class Inciso(BaseModel):
    """Representa um inciso dentro de um artigo ou parágrafo."""
    tipo: Literal["inciso"] = "inciso"
    rotulo: str
    texto: str
    alineas: List[Alinea] = Field(default_factory=list)

class Paragrafo(BaseModel):
    """Representa um parágrafo (ou parágrafo único) dentro de um artigo."""
    tipo: Literal["paragrafo"] = "paragrafo"
    rotulo: str
    texto: str
    incisos: List[Inciso] = Field(default_factory=list)
    alineas: List[Alinea] = Field(default_factory=list) # Para casos onde alíneas estão direto em parágrafos

class Artigo(BaseModel):
    """Representa um artigo, a unidade fundamental do corpo de um ato normativo."""
    tipo: Literal["artigo"] = "artigo"
    numero: str
    rotulo: str
    titulo: Optional[str] = None
    caput: str
    paragrafos: List[Paragrafo] = Field(default_factory=list)
    incisos: List[Inciso] = Field(default_factory=list)

# --- Estruturas Principais ---

class Cabecalho(BaseModel):
    """Representa o cabeçalho de um documento, como ementa e preâmbulo."""
    ementa: Optional[str] = None
    preambulo: Optional[str] = None

class Documento(BaseModel):
    """Representa o corpo principal do ato normativo."""
    id: str
    rotulo: str
    cabecalho: Cabecalho = Field(default_factory=Cabecalho)
    corpo: List[Artigo] = Field(default_factory=list)
    disposicoes_finais: Optional[str] = None
    assinaturas: Optional[str] = None
    revogacoes: Optional[str] = None

class Anexo(BaseModel):
    """Representa um anexo do ato normativo."""
    rotulo: str
    titulo: Optional[str] = None
    conteudo: str
    subanexos: List['Anexo'] = Field(default_factory=list)

class Timestamps(BaseModel):
    """Registra os tempos de início e fim do processamento."""
    inicio_ms: float
    fim_ms: float

class Metadados(BaseModel):
    """Contém metadados sobre a execução do parser."""
    timestamps: Timestamps
    versao_parser: str
    heuristicas: List[str] = Field(default_factory=list)
    erros: List[str] = Field(default_factory=list)

# --- Objeto de Saída Final ---

class ParserOutput(BaseModel):
    """
    O schema final de saída do pipeline de parsing, agregando o documento
    estruturado, seus anexos e os metadados do processamento.
    """
    documento: Documento
    anexos: List[Anexo] = Field(default_factory=list)
    metadados: Metadados

# --- Objeto de Entrada ---

class ParserInput(BaseModel):
    """
    O schema de entrada para o pipeline de parsing.
    """
    id_documento: str
    rotulo: str
    fonte: str
    texto_bruto: str
