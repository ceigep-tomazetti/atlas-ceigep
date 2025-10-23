"""Auditoria por amostragem dos atos ingeridos."""

from __future__ import annotations

import argparse
import json
from datetime import date
from typing import Dict, List, Optional

from src.utils import db as db_utils
from src.utils import storage as storage_utils

# Tipos e períodos para amostragem (tipo_ato, ano inicial, ano final)
SAMPLE_CONFIG = [
    ("lei.ordinária", date(2025, 1, 1), date(2025, 12, 31)),
    ("lei.ordinária", date(2023, 1, 1), date(2023, 12, 31)),
    ("lei.ordinária", date(2020, 1, 1), date(2020, 12, 31)),
    ("decreto.numerado", date(2025, 1, 1), date(2025, 12, 31)),
    ("decreto.numerado", date(2023, 1, 1), date(2023, 12, 31)),
    ("decreto.numerado", date(2020, 1, 1), date(2020, 12, 31)),
    ("portaria.orçamentária", date(2025, 1, 1), date(2025, 12, 31)),
    ("portaria.orçamentária", date(2023, 1, 1), date(2023, 12, 31)),
    ("portaria.orçamentária", date(2020, 1, 1), date(2020, 12, 31)),
]


def _fetch_sample(origin_id: str, tipo: str, start: date, end: date) -> Optional[dict]:
    client = db_utils.get_supabase_client()
    response = (
        client.table("fonte_documento")
        .select("*")
        .eq("fonte_origem_id", origin_id)
        .eq("tipo_ato", tipo)
        .gte("data_legislacao", start.isoformat())
        .lte("data_legislacao", end.isoformat())
        .order("data_legislacao", desc=True)
        .limit(1)
        .execute()
    )
    data = response.data or []
    return data[0] if data else None


def _load_text(registro: dict) -> Dict[str, any]:
    caminho_texto = registro.get("caminho_texto_bruto")
    texto_hash = registro.get("hash_texto_bruto")
    if not caminho_texto:
        return {"status": "missing"}
    texto = storage_utils.download_text(caminho_texto)
    return {
        "status": "ok" if texto.strip() else "empty",
        "tam": len(texto),
        "hash": texto_hash,
    }


def _load_parser_json(registro: dict) -> Dict[str, any]:
    caminho = registro.get("caminho_parser_json")
    if not caminho:
        return {"status": "missing"}
    conteudo = storage_utils.download_text(caminho)
    try:
        parsed = json.loads(conteudo)
    except json.JSONDecodeError as exc:
        return {"status": "invalid", "erro": str(exc)}
    return {
        "status": "ok",
        "dispositivos": len(parsed.get("dispositivos") or []),
        "anexos": len(parsed.get("anexos") or []),
        "fonte_titulo": parsed.get("fonte", {}).get("titulo"),
        "fonte_vigencia": parsed.get("fonte", {}).get("situacao_vigencia"),
    }


def _load_loader_snapshot(registro: dict) -> Dict[str, any]:
    client = db_utils.get_supabase_client()
    response = (
        client.table("ato_normativo")
        .select("id, titulo, status_vigencia, dispositivos:dispositivo(count), anexos:anexo(count)")
        .eq("fonte_documento_id", registro["id"])
        .limit(1)
        .execute()
    )
    data = response.data or []
    if not data:
        return {"status": "pending"}
    row = data[0]

    def _count(value):
        if isinstance(value, list) and value:
            return value[0].get("count")
        if isinstance(value, dict):
            return value.get("count")
        return None

    return {
        "status": "ok",
        "titulo": row.get("titulo"),
        "status_vigencia": row.get("status_vigencia"),
        "dispositivos": _count(row.get("dispositivos")),
        "anexos": _count(row.get("anexos")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audita amostras do pipeline.")
    parser.add_argument("--origin-id", required=True, help="UUID da fonte_origem (ex: Goiás)")
    parser.add_argument("--limit", type=int, help="Limita a quantidade de amostras")
    args = parser.parse_args()

    samples: List[Dict[str, any]] = []
    for item in SAMPLE_CONFIG[: args.limit or len(SAMPLE_CONFIG)]:
        tipo, start, end = item
        registro = _fetch_sample(args.origin_id, tipo, start, end)
        if not registro:
            samples.append(
                {
                    "tipo": tipo,
                    "periodo": f"{start.year}",
                    "status": "sem_registros",
                }
            )
            continue
        resumo = {
            "tipo": tipo,
            "periodo": f"{start.year}",
            "urn": registro.get("urn_lexml"),
            "status": registro.get("status"),
            "status_parsing": registro.get("status_parsing"),
            "status_normalizacao": registro.get("status_normalizacao"),
            "texto": _load_text(registro),
            "parser": _load_parser_json(registro),
            "loader": _load_loader_snapshot(registro),
        }
        samples.append(resumo)

    print(json.dumps(samples, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
