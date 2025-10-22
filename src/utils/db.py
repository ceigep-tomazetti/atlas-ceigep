"""Acesso ao Supabase para o Atlas."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from .status import resolve_status

load_dotenv()


class MissingSupabaseConfig(RuntimeError):
    """Configuração obrigatória do Supabase não encontrada."""


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise MissingSupabaseConfig(
            "Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no ambiente para usar a API do Supabase."
        )
    return create_client(url, key)


def fetch_origens(origin_ids: Optional[List[str]] = None) -> List[dict]:
    client = get_supabase_client()
    query = client.table("fonte_origem").select("*").eq("status", "ativo")
    if origin_ids:
        query = query.in_("id", origin_ids)
    response = query.execute()
    return response.data or []


def find_fonte_documento(fonte_origem_id: str, urn_lexml: str) -> Optional[dict]:
    client = get_supabase_client()
    response = (
        client.table("fonte_documento")
        .select("id")
        .eq("fonte_origem_id", fonte_origem_id)
        .eq("urn_lexml", urn_lexml)
        .limit(1)
        .execute()
    )
    data = response.data or []
    return data[0] if data else None


def insert_fonte_documento(payload: dict) -> None:
    client = get_supabase_client()
    client.table("fonte_documento").insert(payload).execute()


def update_fonte_documento(fonte_origem_id: str, urn_lexml: str, payload: dict) -> None:
    client = get_supabase_client()
    client.table("fonte_documento").update(payload).eq("fonte_origem_id", fonte_origem_id).eq(
        "urn_lexml", urn_lexml
    ).execute()


def registrar_execucao(payload: dict) -> None:
    client = get_supabase_client()
    client.table("fonte_origem_execucao").insert(payload).execute()


def fetch_descobertos(fonte_origem_id: str, limit: Optional[int] = None) -> List[dict]:
    client = get_supabase_client()
    query = (
        client.table("fonte_documento")
        .select("*")
        .eq("fonte_origem_id", fonte_origem_id)
        .eq("status", "descoberto")
        .order("atualizado_em", desc=True)
    )
    if limit:
        query = query.limit(limit)
    response = query.execute()
    return response.data or []


def registrar_sugestao_llm(
    *,
    fonte_documento_id: Optional[str],
    fonte_origem_id: Optional[str],
    urn_lexml: str,
    heuristicas: str,
    json_deterministico: dict,
    json_llm: dict,
    sugestao: str,
) -> None:
    client = get_supabase_client()
    payload = {
        "fonte_documento_id": fonte_documento_id,
        "fonte_origem_id": fonte_origem_id,
        "urn_lexml": urn_lexml,
        "heuristicas": heuristicas,
        "json_deterministico": json_deterministico,
        "json_llm": json_llm,
        "sugestao": sugestao,
    }
    client.table("llm_parser_sugestao").insert(payload).execute()


def fetch_para_parsing(fonte_origem_id: str, limit: Optional[int] = None) -> List[dict]:
    client = get_supabase_client()
    query = (
        client.table("fonte_documento")
        .select("*")
        .eq("fonte_origem_id", fonte_origem_id)
        .eq("status", "processado")
        .eq("status_parsing", "pendente")
        .order("parsing_executado_em", desc=True)
    )
    if limit:
        query = query.limit(limit)
    response = query.execute()
    return response.data or []


def atualizar_parsing_sucesso(
    fonte_origem_id: str,
    urn_lexml: str,
    *,
    caminho: str,
    hash_json: str,
    timestamp_iso: str,
) -> None:
    client = get_supabase_client()
    row = (
        client.table("fonte_documento")
        .select("id,status_normalizacao,caminho_texto_bruto")
        .eq("fonte_origem_id", fonte_origem_id)
        .eq("urn_lexml", urn_lexml)
        .limit(1)
        .execute()
    ).data
    if not row:
        return
    registro = row[0]
    novo_status = resolve_status(
        caminho_texto_bruto=registro.get("caminho_texto_bruto"),
        status_parsing="processado",
        status_normalizacao=registro.get("status_normalizacao"),
    )
    client.table("fonte_documento").update(
        {
            "status_parsing": "processado",
            "parsing_executado_em": timestamp_iso,
            "caminho_parser_json": caminho,
            "hash_parser_json": hash_json,
            "status": novo_status,
        }
    ).eq("id", registro["id"]).execute()


def atualizar_parsing_falha(fonte_origem_id: str, urn_lexml: str, *, timestamp_iso: str) -> None:
    client = get_supabase_client()
    row = (
        client.table("fonte_documento")
        .select("id,status_normalizacao,caminho_texto_bruto")
        .eq("fonte_origem_id", fonte_origem_id)
        .eq("urn_lexml", urn_lexml)
        .limit(1)
        .execute()
    ).data
    if not row:
        return
    registro = row[0]
    novo_status = resolve_status(
        caminho_texto_bruto=registro.get("caminho_texto_bruto"),
        status_parsing="falha",
        status_normalizacao=registro.get("status_normalizacao"),
    )
    client.table("fonte_documento").update(
        {
            "status_parsing": "falha",
            "parsing_executado_em": timestamp_iso,
            "status": novo_status,
        }
    ).eq("id", registro["id"]).execute()
