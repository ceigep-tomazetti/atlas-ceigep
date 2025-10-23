"""Persistência do loader no Supabase."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..utils.db import get_supabase_client
from ..utils.status import resolve_status


class NormativeRepository:
    """Abstrai operações de escrita nas tabelas relacionais."""

    def __init__(self) -> None:
        self.client = get_supabase_client()

    def fetch_para_normalizacao(
        self,
        origem_id: str,
        limit: Optional[int],
        *,
        urns: Optional[List[str]] = None,
    ) -> List[dict]:
        query = (
            self.client.table("fonte_documento")
            .select("*")
            .eq("fonte_origem_id", origem_id)
            .eq("status_parsing", "processado")
            .eq("status_normalizacao", "pendente")
            .order("normalizacao_executado_em", desc=True)
        )
        if urns:
            query = query.in_("urn_lexml", urns)
        if limit and not urns:
            query = query.limit(limit)
        response = query.execute()
        return response.data or []

    def upsert_ato(self, registro: Dict, estrutura: Dict, hash_json: str) -> str:
        fonte_documento_id = registro["id"]
        urn = registro["urn_lexml"]

        fonte_extra = estrutura.get("fonte") or {}
        titulo = fonte_extra.get("titulo") or registro.get("titulo")
        ementa = fonte_extra.get("ementa") or registro.get("ementa")
        tipo_ato = fonte_extra.get("tipo_ato") or registro.get("tipo_ato")

        payload = {
            "fonte_documento_id": fonte_documento_id,
            "urn_lexml": urn,
            "tipo_ato": tipo_ato,
            "titulo": titulo,
            "ementa": ementa,
            "orgao_publicador": registro.get("orgao_publicador"),
            "data_legislacao": registro.get("data_legislacao"),
            "data_publicacao": registro.get("data_publicacao_diario"),
            "status_vigencia": fonte_extra.get("situacao_vigencia"),
            "hash_texto_bruto": registro.get("hash_texto_bruto"),
            "hash_json_estruturado": hash_json,
            "metadata_extra": fonte_extra,
        }

        existing_resp = (
            self.client.table("ato_normativo")
            .select("id")
            .eq("fonte_documento_id", fonte_documento_id)
            .execute()
        )
        existing = existing_resp.data or []

        if existing:
            ato_id = existing[0]["id"]
            self.client.table("ato_normativo").update(payload).eq("id", ato_id).execute()
        else:
            insert_resp = self.client.table("ato_normativo").insert(payload).execute()
            if not insert_resp.data:
                raise RuntimeError("Falha ao inserir ato_normativo")
            ato_id = insert_resp.data[0]["id"]

        return ato_id

    def limpar_componentes(self, ato_id: str) -> None:
        self.client.table("dispositivo_relacao").delete().eq("ato_id", ato_id).execute()
        self.client.table("anexo").delete().eq("ato_id", ato_id).execute()
        self.client.table("dispositivo").delete().eq("ato_id", ato_id).execute()

    def inserir_dispositivo(
        self,
        *,
        ato_id: str,
        parent_id: Optional[str],
        id_lexml: str,
        tipo: str,
        rotulo: Optional[str],
        texto: str,
        ordem: int,
        atributos: Dict,
        hash_texto: Optional[str],
    ) -> str:
        payload = {
            "ato_id": ato_id,
            "parent_id": parent_id,
            "id_lexml": id_lexml,
            "tipo": tipo,
            "rotulo": (rotulo or "")[:160],
            "texto": texto,
            "ordem": ordem,
            "atributos": atributos or {},
            "hash_texto": hash_texto,
        }
        result = self.client.table("dispositivo").insert(payload).execute()
        if not result.data:
            raise RuntimeError("Falha ao inserir dispositivo")
        return result.data[0]["id"]

    def inserir_anexo(
        self,
        *,
        ato_id: str,
        id_lexml: Optional[str],
        titulo: Optional[str],
        texto: str,
        ordem: int,
        hash_texto: Optional[str],
    ) -> None:
        payload = {
            "ato_id": ato_id,
            "id_lexml": id_lexml,
            "titulo": titulo,
            "texto": texto,
            "ordem": ordem,
            "hash_texto": hash_texto,
        }
        self.client.table("anexo").insert(payload).execute()

    def inserir_versao_textual(self, dispositivo_id: str, versao: Dict) -> None:
        payload = {
            "dispositivo_id": dispositivo_id,
            "hash_texto": versao.get("hash_texto"),
            "texto": versao.get("texto"),
            "vigencia_inicio": versao.get("vigencia_inicio"),
            "vigencia_fim": versao.get("vigencia_fim"),
            "origem_alteracao": versao.get("origem_alteracao"),
            "status_vigencia": versao.get("status_vigencia"),
            "anotacoes": versao.get("anotacoes", {}),
        }
        self.client.table("versao_textual").upsert(payload, on_conflict="dispositivo_id,hash_texto").execute()

    def inserir_relacao(self, ato_id: str, relacao: Dict) -> None:
        payload = {
            "ato_id": ato_id,
            "dispositivo_origem_id": relacao.get("dispositivo_origem_id"),
            "dispositivo_alvo_id": relacao.get("dispositivo_alvo_id"),
            "urn_alvo": relacao.get("urn_alvo"),
            "tipo": relacao.get("tipo"),
            "descricao": relacao.get("descricao"),
        }
        self.client.table("dispositivo_relacao").insert(payload).execute()

    def marcar_normalizado(self, registro: Dict) -> None:
        novo_status = resolve_status(
            caminho_texto_bruto=registro.get("caminho_texto_bruto"),
            status_parsing=registro.get("status_parsing"),
            status_normalizacao="processado",
        )
        payload = {
            "status_normalizacao": "processado",
            "normalizacao_executado_em": datetime.utcnow().isoformat(),
            "status": novo_status,
        }
        self.client.table("fonte_documento").update(payload).eq("id", registro["id"]).execute()
