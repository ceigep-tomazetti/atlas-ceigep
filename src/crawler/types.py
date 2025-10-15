"""Tipos auxiliares para o crawler de descoberta."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional


@dataclass
class FonteDescoberta:
    """Representa um ato identificado durante a fase de descoberta."""

    fonte_origem_id: str
    urn_lexml: str
    url_fonte: str
    tipo_ato: Optional[str] = None
    titulo: Optional[str] = None
    ementa: Optional[str] = None
    data_legislacao: Optional[date] = None
    data_publicacao_diario: Optional[date] = None
    orgao_publicador: Optional[str] = None
    metadados_brutos: Dict[str, Any] = None

    def as_db_params(self) -> Dict[str, Any]:
        """Formata o registro para inserção na tabela fonte_documento."""
        return {
            "fonte_origem_id": self.fonte_origem_id,
            "urn_lexml": self.urn_lexml,
            "url_fonte": self.url_fonte,
            "tipo_ato": self.tipo_ato,
            "titulo": self.titulo,
            "ementa": self.ementa,
            "data_legislacao": self.data_legislacao.isoformat() if self.data_legislacao else None,
            "data_publicacao_diario": self.data_publicacao_diario.isoformat() if self.data_publicacao_diario else None,
            "orgao_publicador": self.orgao_publicador,
            "metadados_brutos": self.metadados_brutos or {},
        }
