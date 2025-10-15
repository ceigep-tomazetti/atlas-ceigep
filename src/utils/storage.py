"""Helpers para trabalhar com o Supabase Storage."""

from __future__ import annotations

import os
from pathlib import PurePosixPath
import unicodedata
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

BUCKET_TEXTOS_BRUTOS = "textos_brutos"


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
    bucket.upload(
        relative_path,
        content.encode("utf-8"),
        file_options={"content-type": "text/plain", "upsert": "true"},
    )
    return path
