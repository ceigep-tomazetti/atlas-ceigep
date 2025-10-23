"""Utilitários para dividir textos extensos em chunks seguros para o parser LLM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ..utils import llm as llm_utils

DEFAULT_MAX_CHARS = 15000


@dataclass
class TextoChunk:
    """Representa um trecho sequencial do texto bruto."""

    indice: int
    inicio: int
    fim: int
    texto: str


def _detectar_limite_seguro(
    trecho: str,
    registro: Dict,
    *,
    offset_inicial: int,
    model: Optional[str],
) -> Optional[int]:
    """Usa o LLM auxiliar para localizar o último dispositivo completo dentro do trecho."""
    try:
        resposta = llm_utils.detectar_limite_dispositivo(
            trecho,
            registro,
            offset_inicial=offset_inicial,
            model=model,
        )
    except Exception:  # noqa: BLE001
        return None

    if resposta is None:
        return None
    if resposta <= 0 or resposta > len(trecho):
        return None
    return resposta


def gerar_chunks(
    texto_bruto: str,
    registro: Dict,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    aux_model: Optional[str] = None,
) -> List[TextoChunk]:
    """Divide o texto em chunks, respeitando limites informados pelo LLM para não quebrar dispositivos."""
    if len(texto_bruto) <= max_chars:
        return [TextoChunk(indice=0, inicio=0, fim=len(texto_bruto), texto=texto_bruto)]

    chunks: List[TextoChunk] = []
    inicio = 0
    indice = 0
    total_len = len(texto_bruto)

    while inicio < total_len:
        limite_candidato = min(inicio + max_chars, total_len)
        if limite_candidato >= total_len:
            chunks.append(TextoChunk(indice=indice, inicio=inicio, fim=total_len, texto=texto_bruto[inicio:]))
            break

        trecho = texto_bruto[inicio:limite_candidato]
        limite_relativo = _detectar_limite_seguro(
            trecho,
            registro,
            offset_inicial=inicio,
            model=aux_model,
        )

        if limite_relativo is None:
            # Não foi possível determinar um limite seguro – anexar o restante e encerrar.
            chunks.append(TextoChunk(indice=indice, inicio=inicio, fim=total_len, texto=texto_bruto[inicio:]))
            break

        fim = inicio + limite_relativo
        if fim <= inicio:
            chunks.append(TextoChunk(indice=indice, inicio=inicio, fim=total_len, texto=texto_bruto[inicio:]))
            break

        chunks.append(TextoChunk(indice=indice, inicio=inicio, fim=fim, texto=texto_bruto[inicio:fim]))
        inicio = fim
        indice += 1

        if inicio >= total_len:
            break

    return chunks


def combinar_resultados(chunk_results: List[Dict]) -> Dict:
    """Une os resultados JSON retornados pelos chunks em uma única estrutura."""
    if not chunk_results:
        return {"dispositivos": [], "anexos": [], "relacoes": []}

    combinado: Dict = {
        "fonte": {},
        "dispositivos": [],
        "anexos": [],
        "relacoes": [],
        "metadados_origem": None,
    }

    for resultado in chunk_results:
        if not combinado["fonte"] and resultado.get("fonte"):
            combinado["fonte"] = resultado["fonte"]
        if combinado.get("metadados_origem") is None and resultado.get("metadados_origem") is not None:
            combinado["metadados_origem"] = resultado.get("metadados_origem")

        combinado["dispositivos"].extend(resultado.get("dispositivos") or [])
        combinado["anexos"].extend(resultado.get("anexos") or [])
        combinado["relacoes"].extend(resultado.get("relacoes") or [])

    return combinado


def montar_chunk_info(chunk: TextoChunk, total_chunks: int) -> Dict[str, int]:
    """Retorna metadados que serão incorporados ao prompt."""
    return {
        "indice": chunk.indice,
        "total": total_chunks,
        "offset_inicio": chunk.inicio,
        "offset_fim": chunk.fim,
    }
