"""Helpers para consolidar status das etapas do pipeline."""

from __future__ import annotations

from typing import Optional


def resolve_status(
    *,
    caminho_texto_bruto: Optional[str],
    status_parsing: Optional[str],
    status_normalizacao: Optional[str],
) -> str:
    """Retorna o status unificado baseado nas etapas já concluídas."""

    if status_normalizacao == "processado":
        return "normalizado"
    if status_parsing == "processado":
        return "parsing"
    if caminho_texto_bruto:
        return "processado"
    return "descoberto"

