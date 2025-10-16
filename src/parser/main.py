"""CLI do parser determinístico do Atlas."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
from datetime import datetime
from typing import Dict, Iterable, Optional

from ..utils import db as db_utils
from ..utils import storage as storage_utils
from ..utils import llm as llm_utils
from .deterministic import describe_heuristics, parse_ato, resumir_dispositivos

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _normalizar_llm_result(bruto: Dict, fallback: Dict, texto_bruto: str) -> Dict:
    resultado = dict(bruto)
    resultado.setdefault("gerado_em", _now_iso())
    resultado["texto_bruto"] = texto_bruto

    dispositivos = resultado.get("dispositivos")
    if not isinstance(dispositivos, list) or not dispositivos:
        resultado["dispositivos"] = fallback.get("dispositivos", [])

    anexos = resultado.get("anexos")
    if not isinstance(anexos, list):
        resultado["anexos"] = []

    fonte = resultado.get("fonte") or {}
    fonte_fallback = fallback.get("fonte", {})
    for chave, valor in fonte_fallback.items():
        fonte.setdefault(chave, valor)
    resultado["fonte"] = fonte
    return resultado


def _comparar_resultados(det: Dict, llm: Dict, urn: str) -> None:
    det_disps = len(det.get("dispositivos", []) or [])
    llm_disps = len(llm.get("dispositivos", []) or [])
    det_anexos = len(det.get("anexos", []) or [])
    llm_anexos = len(llm.get("anexos", []) or [])
    logging.info(
        "Comparativo %s: determinístico %s dispositivos/%s anexos vs LLM %s dispositivos/%s anexos.",
        urn,
        det_disps,
        det_anexos,
        llm_disps,
        llm_anexos,
    )


def _sanear_para_comparacao(payload: Dict) -> Dict:
    def limpar(valor):
        if isinstance(valor, dict):
            return {chave: limpar(item) for chave, item in valor.items() if chave != "ordem"}
        if isinstance(valor, list):
            return [limpar(item) for item in valor]
        return valor

    estrutura_limpa = limpar(payload)
    dispositivos = estrutura_limpa.get("dispositivos")
    if isinstance(dispositivos, list):
        dispositivos_filtrados = [
            dispositivo
            for dispositivo in dispositivos
            if dispositivo.get("rotulo") not in {"preambulo", "disposicao_final"}
        ]
    else:
        dispositivos_filtrados = []

    anexos = estrutura_limpa.get("anexos")
    anexos_lista = anexos if isinstance(anexos, list) else []

    return {
        "dispositivos": dispositivos_filtrados,
        "anexos": anexos_lista,
    }


def _json_equivalentes(det: Dict, llm: Dict) -> bool:
    det_limpo = _sanear_para_comparacao(det)
    llm_limpo = _sanear_para_comparacao(llm)
    det_dump = json.dumps(det_limpo, sort_keys=True, ensure_ascii=False)
    llm_dump = json.dumps(llm_limpo, sort_keys=True, ensure_ascii=False)
    return det_dump == llm_dump


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Parser determinístico para textos brutos do Atlas")
    parser.add_argument("--origin-id", action="append", help="UUID da fonte_origem a processar (pode repetir).")
    parser.add_argument("--limit", type=int, help="Limite de itens por origem.")
    parser.add_argument("--dry-run", action="store_true", help="Executa sem salvar JSON nem atualizar o banco.")
    parser.add_argument(
        "--mode",
        choices=["deterministic", "llm", "both", "review"],
        default="deterministic",
        help="Modo de execução: heurístico, LLM, ambos (debug) ou revisão (comparar e bloquear divergências).",
    )
    parser.add_argument("--llm-model", help="Modelo Gemini a ser utilizado (opcional).")
    parser.add_argument(
        "--review-sample-ratio",
        type=float,
        default=1.0,
        help="Proporção (0-1) de itens verificados por LLM no modo review. 1.0 = 100%%.",
    )
    parser.add_argument(
        "--review-sample-seed",
        type=int,
        help="Seed opcional para tornar determinística a amostragem do modo review.",
    )

    args = parser.parse_args(argv)

    if not 0.0 <= args.review_sample_ratio <= 1.0:
        parser.error("--review-sample-ratio deve estar entre 0 e 1.")

    origens = db_utils.fetch_origens(args.origin_id)
    if not origens:
        logging.warning("Nenhuma origem ativa encontrada para os critérios fornecidos.")
        return

    heuristicas_texto = describe_heuristics()
    rng = random.Random(args.review_sample_seed) if args.review_sample_seed is not None else random.Random()

    if args.mode == "review" and args.review_sample_ratio < 1.0:
        logging.info(
            "Modo review com amostragem de %.1f%% (seed=%s).",
            args.review_sample_ratio * 100,
            args.review_sample_seed if args.review_sample_seed is not None else "aleatória",
        )

    for origem in origens:
        origem_id = str(origem["id"])
        registros = db_utils.fetch_para_parsing(origem_id, args.limit)
        if not registros:
            logging.info("Nenhum item pendente de parsing na origem %s.", origem_id)
            continue

        processados = 0
        for registro in registros:
            urn = registro["urn_lexml"]
            caminho_texto = registro.get("caminho_texto_bruto")
            if not caminho_texto:
                logging.warning("Registro %s sem caminho de texto bruto. Marcando como falha.", urn)
                if not args.dry_run:
                    db_utils.atualizar_parsing_falha(origem_id, urn, timestamp_iso=_now_iso())
                continue

            try:
                texto = storage_utils.download_text(caminho_texto)
            except Exception as exc:  # noqa: BLE001
                logging.exception("Falha ao baixar texto bruto de %s: %s", urn, exc)
                if not args.dry_run:
                    db_utils.atualizar_parsing_falha(origem_id, urn, timestamp_iso=_now_iso())
                continue

            resultado_det = parse_ato(registro, texto)
            resultado_det.setdefault("anexos", [])
            resultado_final = resultado_det
            resumo_det = resumir_dispositivos(resultado_det["dispositivos"], max_itens=None)

            logging.info("URN %s – resultado determinístico: %s dispositivos.", urn, len(resultado_det["dispositivos"]))

            resultado_llm = None
            review_mode = args.mode == "review"
            selecionado_para_review = False
            if review_mode and args.review_sample_ratio > 0:
                selecionado_para_review = rng.random() <= args.review_sample_ratio
                if not selecionado_para_review:
                    logging.info("URN %s – revisão por LLM pulada (amostragem).", urn)

            precisa_llm = False
            if args.mode in {"llm", "both"}:
                precisa_llm = True
            elif review_mode and selecionado_para_review:
                precisa_llm = True

            if precisa_llm:
                try:
                    bruto_llm = llm_utils.gerar_estrutura_llm(
                        texto,
                        registro,
                        heuristicas=heuristicas_texto,
                        model=args.llm_model,
                    )
                    resultado_llm = _normalizar_llm_result(bruto_llm, resultado_det, texto)
                    logging.info(
                        "URN %s – resultado LLM: %s dispositivos, %s anexos.",
                        urn,
                        len(resultado_llm.get("dispositivos", [])),
                        len(resultado_llm.get("anexos", [])),
                    )
                    if args.mode in {"both", "review"}:
                        _comparar_resultados(resultado_det, resultado_llm, urn)
                    if args.mode == "llm":
                        resultado_final = resultado_llm
                except llm_utils.LLMNotConfigured as exc:
                    logging.warning("LLM não configurado (%s). Mantendo saída determinística.", exc)
                    resultado_llm = None
                except Exception as exc:  # noqa: BLE001
                    logging.exception("Falha no LLM para %s. Mantendo saída determinística.", urn)
                    resultado_llm = None

            if review_mode:
                if not selecionado_para_review:
                    logging.debug("URN %s – validação determinística concluída (sem revisão por amostragem).", urn)
                    # segue fluxo normal com resultado determinístico
                    pass
                else:
                    if resultado_llm is None:
                        logging.warning("URN %s – LLM indisponível no modo review. Marcando para reprocessar.", urn)
                        if not args.dry_run:
                            db_utils.atualizar_parsing_falha(origem_id, urn, timestamp_iso=_now_iso())
                        continue
                    if _json_equivalentes(resultado_det, resultado_llm):
                        logging.info("URN %s – Fit 100%% entre parser determinístico e LLM.", urn)
                        resultado_final = resultado_det
                    else:
                        logging.warning("URN %s – Divergência detectada entre parser determinístico e LLM.", urn)
                        sugestao_texto = None
                        try:
                            sugestao_texto = llm_utils.gerar_revisao_regex(
                                texto,
                                resultado_det,
                                resultado_llm,
                                heuristicas=heuristicas_texto,
                                model=args.llm_model,
                            )
                            logging.info("Sugestões LLM para %s:\n%s", urn, sugestao_texto)
                        except llm_utils.LLMNotConfigured:
                            logging.warning("LLM não configurado para revisão detalhada.")
                        except Exception as exc:  # noqa: BLE001
                            logging.exception("Falha ao gerar sugestões de regex para %s: %s", urn, exc)
                        if args.dry_run:
                            if sugestao_texto:
                                print(sugestao_texto)
                            print("--- Divergência detectada; registro marcado como falha (dry-run).\n")
                            continue
                        if sugestao_texto:
                            try:
                                db_utils.registrar_sugestao_llm(
                                    fonte_documento_id=registro.get("id"),
                                    fonte_origem_id=origem_id,
                                    urn_lexml=urn,
                                    heuristicas=heuristicas_texto,
                                    json_deterministico=resultado_det,
                                    json_llm=resultado_llm,
                                    sugestao=sugestao_texto,
                                )
                            except Exception as exc:  # noqa: BLE001
                                logging.exception("Falha ao registrar sugestão LLM para %s: %s", urn, exc)
                        db_utils.atualizar_parsing_falha(origem_id, urn, timestamp_iso=_now_iso())
                        continue

            if review_mode and not selecionado_para_review:
                resultado_llm = None  # garante que bloco dry-run não imprime estrutura LLM inexistente

            # Logs e saída para debug
            if args.dry_run:
                print(f"\n=== Texto bruto normalizado ({urn}) ===\n{resultado_det['texto_bruto']}\n")
                print(f"--- Dispositivos determinísticos ({urn}) ---")
                for linha in resumo_det:
                    print(linha)
                if resultado_llm is not None:
                    print(f"\n--- Dispositivos LLM ({urn}) ---")
                    for linha in resumir_dispositivos(resultado_llm.get("dispositivos", []), max_itens=None):
                        print(linha)
                print("--- fim ---\n")
                processados += 1
                continue

            json_str = json.dumps(resultado_final, ensure_ascii=False, indent=2)
            hash_json = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

            try:
                caminho_json = storage_utils.upload_parser_json(urn, json_str)
                db_utils.atualizar_parsing_sucesso(
                    origem_id,
                    urn,
                    caminho=caminho_json,
                    hash_json=hash_json,
                    timestamp_iso=_now_iso(),
                )
                processados += 1
            except Exception as exc:  # noqa: BLE001
                logging.exception("Falha ao salvar JSON estruturado de %s: %s", urn, exc)
                db_utils.atualizar_parsing_falha(origem_id, urn, timestamp_iso=_now_iso())

        logging.info(
            "Parsing concluído para origem %s: %s itens %sprocessados.",
            origem_id,
            processados,
            "dry-run " if args.dry_run else "",
        )


if __name__ == "__main__":
    main()
