"""Script auxiliar para depurar a resposta do LLM para um ato específico."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.parser.main import LLM_HEURISTICS_INFO
from src.utils import db as db_utils
from src.utils import llm as llm_utils
from src.utils import storage as storage_utils


def _fetch_registro(origin_id: str, urn: str) -> dict:
    client = db_utils.get_supabase_client()
    response = (
        client.table("fonte_documento")
        .select("*")
        .eq("fonte_origem_id", origin_id)
        .eq("urn_lexml", urn)
        .limit(1)
        .execute()
    )
    data = response.data or []
    if not data:
        raise SystemExit(f"Nenhum registro encontrado para origem={origin_id} e urn={urn}.")
    return data[0]


def _call_llm(registro: dict, texto: str, *, model: str | None) -> tuple[str, str]:
    if llm_utils.genai is None:
        raise SystemExit("Pacote google-generativeai não está instalado.")

    config = llm_utils._get_config(model)  # pylint: disable=protected-access
    llm_utils.genai.configure(api_key=config.api_key)
    prompt = llm_utils._build_prompt(texto, registro, LLM_HEURISTICS_INFO)  # pylint: disable=protected-access

    modelo = llm_utils.genai.GenerativeModel(config.model)
    resposta = modelo.generate_content(prompt)  # type: ignore[no-untyped-call]
    if not resposta.candidates:
        raise RuntimeError("Resposta vazia do LLM.")

    texto_resposta = resposta.candidates[0].content.parts[0].text  # type: ignore[attr-defined]
    json_str = llm_utils._extract_first_json_block(texto_resposta)  # pylint: disable=protected-access
    return texto_resposta, json_str


def main() -> None:
    parser = argparse.ArgumentParser(description="Depura a saída do LLM para um ato específico.")
    parser.add_argument("--origin-id", required=True, help="UUID da fonte_origem.")
    parser.add_argument("--urn", required=True, help="URN LexML completa do ato.")
    parser.add_argument("--llm-model", help="Modelo Gemini opcional.")
    parser.add_argument(
        "--output",
        help="Arquivo para salvar a resposta JSON (tanto bruta quanto após reparo manual).",
    )

    args = parser.parse_args()

    registro = _fetch_registro(args.origin_id, args.urn)
    caminho_texto = registro.get("caminho_texto_bruto")
    if not caminho_texto:
        raise SystemExit("Registro não possui caminho_texto_bruto definido.")

    texto_bruto = storage_utils.download_text(caminho_texto)

    try:
        resposta_completa, json_str = _call_llm(registro, texto_bruto, model=args.llm_model)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Falha ao executar o LLM: {exc}") from exc

    print("=== Resposta completa do LLM ===")
    print(resposta_completa)
    print("\n=== Bloco JSON extraído ===")
    print(json_str)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json_str, encoding="utf-8")
        print(f"\nBloco JSON salvo em {output_path}")

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as exc:  # pragma: no cover - fluxo de depuração
        print("\nJSON inválido. Erro reportado:")
        print(exc)
        sys.exit(1)

    print("\nJSON válido. Resumo:")
    dispositivos = len(parsed.get("dispositivos") or [])
    anexos = len(parsed.get("anexos") or [])
    print(f"Dispositivos: {dispositivos}")
    print(f"Anexos: {anexos}")


if __name__ == "__main__":
    main()
