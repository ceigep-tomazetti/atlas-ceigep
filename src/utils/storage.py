"""Helpers para trabalhar com o Supabase Storage."""

from __future__ import annotations

import os
import time
from pathlib import PurePosixPath
import unicodedata
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

BUCKET_TEXTOS_BRUTOS = "textos_brutos"
BUCKET_PARSER_JSON = "textos_estruturados"


def _get_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórios")
    return create_client(url, key)


def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.replace(" ", ".").replace("/", ".").lower()
    return value


def build_storage_path(urn: str) -> str:
    parts = urn.split(";")
    sanitized = [_slugify(part) for part in parts]
    chave = PurePosixPath(*sanitized)
    return f"{BUCKET_TEXTOS_BRUTOS}/{chave}.txt"


def upload_text(urn: str, content: str) -> str:
    client = _get_client()
    path = build_storage_path(urn)
    bucket = client.storage.from_(BUCKET_TEXTOS_BRUTOS)
    relative_path = path[len(BUCKET_TEXTOS_BRUTOS) + 1 :]
    attempts = 0
    backoff = 0.5

    while True:
        try:
            bucket.upload(
                relative_path,
                content.encode("utf-8"),
                file_options={"content-type": "text/plain", "upsert": "true"},
            )
            break
        except Exception as exc:  # noqa: BLE001
            attempts += 1
            if attempts >= 3:
                raise
            time.sleep(backoff)
            backoff *= 2
    return path


def _split_bucket_path(path: str):
    if "/" not in path:
        raise ValueError(f"Caminho inválido para storage: {path}")
    bucket, key = path.split("/", 1)
    return bucket, key


def download_text(path: str) -> str:
    client = _get_client()
    bucket, key = _split_bucket_path(path)
    data = client.storage.from_(bucket).download(key)
    return data.decode("utf-8")


def build_parser_json_path(urn: str) -> str:
    parts = urn.split(";")
    sanitized = [_slugify(part) for part in parts]
    chave = PurePosixPath(*sanitized)
    return f"{BUCKET_PARSER_JSON}/{chave}.json"


def upload_parser_json(urn: str, content: str) -> str:
    client = _get_client()
    path = build_parser_json_path(urn)
    relative_path = path[len(BUCKET_PARSER_JSON) + 1 :]
    bucket = client.storage.from_(BUCKET_PARSER_JSON)
    bucket.upload(
        relative_path,
        content.encode("utf-8"),
        file_options={"content-type": "application/json", "upsert": "true"},
    )
    return path
