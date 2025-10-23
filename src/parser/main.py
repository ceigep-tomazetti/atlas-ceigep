"""CLI para parsing de atos usando exclusivamente o LLM."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import unicodedata
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from ..utils import db as db_utils
from ..utils import llm as llm_utils
from ..utils import storage as storage_utils
from . import chunking

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

LLM_HEURISTICS_INFO = (
    "Parser heurístico desativado por ora. Gere a estrutura LexML completa apenas com o LLM."
)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _normalizar_llm_result(bruto: Dict, registro: Dict, texto_bruto: str) -> Dict:
    """Garante campos mínimos (fonte, anexos, metadados) na saída do LLM."""
    resultado = dict(bruto)
    resultado.setdefault("gerado_em", _now_iso())
    resultado["texto_bruto"] = texto_bruto

    dispositivos = resultado.get("dispositivos")
    if not isinstance(dispositivos, list):
        resultado["dispositivos"] = []

    anexos = resultado.get("anexos")
    if not isinstance(anexos, list):
        resultado["anexos"] = []

    fonte_padrao = {
        "urn_lexml": registro.get("urn_lexml"),
        "tipo_ato": registro.get("tipo_ato"),
        "titulo": registro.get("titulo"),
        "ementa": registro.get("ementa"),
        "data_legislacao": registro.get("data_legislacao"),
        "data_publicacao_diario": registro.get("data_publicacao_diario"),
        "orgao_publicador": registro.get("orgao_publicador"),
        "url_fonte": registro.get("url_fonte"),
    }
    fonte_atual = resultado.get("fonte") or {}
    for chave, valor in fonte_padrao.items():
        fonte_atual.setdefault(chave, valor)
    resultado["fonte"] = fonte_atual

    metadados = registro.get("metadados_brutos")
    if isinstance(metadados, str):
        try:
            metadados = json.loads(metadados)
        except json.JSONDecodeError:
            pass
    resultado.setdefault("metadados_origem", metadados)

    dispositivos = resultado.get("dispositivos")
    if isinstance(dispositivos, list) and dispositivos:
        _atribuir_ids_lexml(dispositivos)

    if not isinstance(resultado.get("relacoes"), list):
        resultado["relacoes"] = []

    return resultado


def _resumir_dispositivos(dispositivos: List[Dict], *, max_itens: Optional[int] = 5) -> List[str]:
    """Gera linhas curtas para inspeção no modo --dry-run."""
    linhas: List[str] = []
    dispositivos_iter = dispositivos if max_itens is None else dispositivos[:max_itens]
    for dispositivo in dispositivos_iter:
        rotulo = dispositivo.get("rotulo", "(sem rótulo)")
        texto = dispositivo.get("texto", "").replace("\n", " ")
        linhas.append(f"{rotulo}: {texto}")
        filhos = dispositivo.get("filhos", [])
        filhos_iter = filhos if max_itens is None else filhos[:max_itens]
        for filho in filhos_iter:
            rotulo_filho = filho.get("rotulo", "(filho)")
            texto_filho = filho.get("texto", "").replace("\n", " ")
            linhas.append(f"  * {rotulo_filho}: {texto_filho}")
    return linhas


def _normalizar_rotulo(rotulo: str) -> str:
    texto = (rotulo or "").replace("º", "").replace("°", "")
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto.strip()


ROMAN_NUMERAL_RE = re.compile(r"^(M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))$", re.IGNORECASE)


def _classificar_dispositivo(rotulo: str) -> Tuple[str, Optional[str]]:
    texto = _normalizar_rotulo(rotulo)
    upper = texto.upper()

    if not texto:
        return "dispositivo_auxiliar", None

    padrao_valor = None

    mapa_topo = (
        ("titulo", re.compile(r"^TITULO\s+([IVXLCDM]+)", re.IGNORECASE)),
        ("livro", re.compile(r"^LIVRO\s+([IVXLCDM]+)", re.IGNORECASE)),
        ("parte", re.compile(r"^PARTE\s+([IVXLCDM]+)", re.IGNORECASE)),
        ("capitulo", re.compile(r"^CAPITULO\s+(UNICO|[IVXLCDM]+)", re.IGNORECASE)),
        ("secao", re.compile(r"^SECAO\s+(UNICA|[IVXLCDM]+)", re.IGNORECASE)),
        ("subsecao", re.compile(r"^SUBSECAO\s+(UNICA|[IVXLCDM]+)", re.IGNORECASE)),
    )
    for tipo, padrao in mapa_topo:
        match = padrao.match(texto)
        if match:
            valor = match.group(1).lower()
            valor = valor.replace("º", "").replace("°", "")
            valor = valor.replace("unica", "unica")
            return tipo, valor

    artigo = re.search(r"ART\.?\s*(\d+[A-Z]?)", upper)
    if artigo:
        valor = artigo.group(1).lower().replace("º", "")
        return "artigo", valor

    if upper.startswith("PARAGRAFO"):
        if "UNICO" in upper:
            return "paragrafo_unico", None
        match = re.search(r"PARAGRAFO\s+(\d+)", upper)
        if match:
            return "paragrafo", match.group(1)

    if texto.startswith("§"):
        match = re.search(r"§\s*(\d+)", texto)
        if match:
            return "paragrafo", match.group(1)
        if "UNICO" in upper:
            return "paragrafo_unico", None

    if upper.startswith("INCISO"):
        match = re.search(r"INCISO\s+([IVXLCDM]+)", upper)
        if match:
            return "inciso", match.group(1).lower()

    inciso_romano = re.match(r"^([IVXLCDM]+)", upper)
    if inciso_romano and ROMAN_NUMERAL_RE.match(inciso_romano.group(1)):
        return "inciso", inciso_romano.group(1).lower()

    if upper.startswith("ALINEA"):
        match = re.search(r"ALINEA\s+([A-Z])", upper)
        if match:
            return "alinea", match.group(1).lower()

    alinea_letra = re.match(r"^([a-z])\)", texto)
    if alinea_letra:
        return "alinea", alinea_letra.group(1).lower()

    if upper.startswith("ITEM"):
        match = re.search(r"ITEM\s+(\d+)", upper)
        if match:
            return "item", match.group(1)

    item_numerico = re.match(r"^(\d+)\)", texto)
    if item_numerico:
        return "item", item_numerico.group(1)

    return "dispositivo_auxiliar", None


PREFIXOS = {
    "titulo": "tit",
    "livro": "liv",
    "parte": "par",
    "capitulo": "cap",
    "secao": "sec",
    "subsecao": "subsec",
    "artigo": "art",
    "paragrafo": "p",
    "paragrafo_unico": "pu",
    "inciso": "inc",
    "alinea": "ali",
    "item": "item",
}


def _atribuir_ids_lexml(dispositivos: List[Dict]) -> None:
    def rec(nodes: List[Dict], parent_id: Optional[str] = None) -> None:
        nivel_contadores: Dict[str, int] = {}
        for idx, node in enumerate(nodes, start=1):
            rotulo = node.get("rotulo", "")
            tipo, valor = _classificar_dispositivo(rotulo)
            nivel_contadores[tipo] = nivel_contadores.get(tipo, 0) + 1

            if tipo == "artigo":
                sufixo = valor or str(nivel_contadores[tipo])
                current_id = f"art{sufixo}"
            elif tipo == "paragrafo":
                sufixo = valor or str(nivel_contadores[tipo])
                base = parent_id or f"disp{idx}"
                current_id = f"{base}p{sufixo}"
            elif tipo == "paragrafo_unico":
                base = parent_id or f"disp{idx}"
                current_id = f"{base}pu"
            elif tipo == "inciso":
                sufixo = (valor or str(nivel_contadores[tipo])).lower()
                base = parent_id or f"disp{idx}"
                current_id = f"{base}inc{sufixo}"
            elif tipo == "alinea":
                sufixo = (valor or str(nivel_contadores[tipo])).lower()
                base = parent_id or f"disp{idx}"
                current_id = f"{base}ali{sufixo}"
            elif tipo == "item":
                sufixo = valor or str(nivel_contadores[tipo])
                base = parent_id or f"disp{idx}"
                current_id = f"{base}item{sufixo}"
            elif tipo in PREFIXOS and parent_id is None:
                sufixo = (valor or str(nivel_contadores[tipo])).lower()
                current_id = f"{PREFIXOS[tipo]}{sufixo}"
            elif tipo in PREFIXOS:
                sufixo = (valor or str(nivel_contadores[tipo])).lower()
                base = parent_id or f"disp{idx}"
                current_id = f"{base}{PREFIXOS[tipo]}{sufixo}"
            else:
                base = parent_id or "disp"
                current_id = f"{base}_{idx}"

            node["id_lexml"] = current_id
            node["tipo"] = tipo

            filhos = node.get("filhos")
            if isinstance(filhos, list) and filhos:
                rec(filhos, current_id)

    rec(dispositivos)


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Parser LLM para textos brutos do Atlas")
    parser.add_argument("--origin-id", action="append", help="UUID da fonte_origem a processar (pode repetir).")
    parser.add_argument("--limit", type=int, help="Limite de itens por origem.")
    parser.add_argument(
        "--urn",
        action="append",
        help="URN LexML específica a processar (pode informar múltiplas vezes). Ignora --limit.",
    )
    parser.add_argument("--year", type=int, help="Ano (YYYY) para filtrar `data_legislacao`.")
    parser.add_argument("--dry-run", action="store_true", help="Executa sem salvar JSON nem atualizar o banco.")
    parser.add_argument("--llm-model", help="Modelo Gemini a ser utilizado (opcional).")

    args = parser.parse_args(argv)

    origens = db_utils.fetch_origens(args.origin_id)
    if not origens:
        logging.warning("Nenhuma origem ativa encontrada para os critérios fornecidos.")
        return

    for origem in origens:
        origem_id = str(origem["id"])
        urns_filtradas = list(dict.fromkeys(args.urn)) if args.urn else None
        registros = db_utils.fetch_para_parsing(
            origem_id,
            args.limit,
            urns=urns_filtradas,
            year=args.year,
        )
        if not registros:
            if urns_filtradas:
                logging.info(
                    "Nenhum item encontrado para as URNs fornecidas na origem %s.",
                    origem_id,
                )
            elif args.year:
                logging.info(
                    "Nenhum item pendente de parsing na origem %s para o ano %s.",
                    origem_id,
                    args.year,
                )
            else:
                logging.info("Nenhum item pendente de parsing na origem %s.", origem_id)
            continue

        if urns_filtradas:
            logging.info("Processando %s URN(s) específicas.", len(registros))
        elif args.year:
            logging.info(
                "Processando até %s item(ns) da origem %s filtrados por ano %s.",
                len(registros) if args.limit else "todos",
                origem_id,
                args.year,
            )

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

            logging.info("Preparando chunking para %s.", urn)
            try:
                chunks = chunking.gerar_chunks(
                    texto,
                    registro,
                    aux_model=args.llm_model,
                )
            except Exception as exc:  # noqa: BLE001
                logging.exception("Falha ao planejar chunking para %s.", urn)
                if not args.dry_run:
                    db_utils.atualizar_parsing_falha(origem_id, urn, timestamp_iso=_now_iso())
                continue

            chunk_total = len(chunks)
            chunk_resultados: List[Dict] = []
            falha_chunk = False

            logging.info("URN %s – processará %s chunk%s.", urn, chunk_total, "" if chunk_total == 1 else "s")

            for chunk in chunks:
                chunk_info = chunking.montar_chunk_info(chunk, chunk_total)
                logging.info(
                    "URN %s – enviando chunk %s/%s ao LLM (tamanho %s caracteres).",
                    urn,
                    chunk.indice + 1,
                    chunk_total,
                    len(chunk.texto),
                )
                try:
                    bruto_llm = llm_utils.gerar_estrutura_llm(
                        chunk.texto,
                        registro,
                        heuristicas=LLM_HEURISTICS_INFO,
                        model=args.llm_model,
                        chunk_info=chunk_info,
                    )
                except llm_utils.LLMNotConfigured as exc:
                    logging.error("LLM não configurado (%s). Interrompendo execução.", exc)
                    if not args.dry_run:
                        db_utils.atualizar_parsing_falha(origem_id, urn, timestamp_iso=_now_iso())
                    return
                except Exception as exc:  # noqa: BLE001
                    logging.exception(
                        "Falha ao executar o LLM para %s (chunk %s/%s).",
                        urn,
                        chunk.indice + 1,
                        chunk_total,
                    )
                    if not args.dry_run:
                        db_utils.atualizar_parsing_falha(origem_id, urn, timestamp_iso=_now_iso())
                    falha_chunk = True
                    break

                chunk_resultados.append(bruto_llm)

            if falha_chunk:
                continue

            bruto_combined = chunking.combinar_resultados(chunk_resultados)
            resultado_llm = _normalizar_llm_result(bruto_combined, registro, texto)
            logging.info(
                "URN %s – LLM retornou %s dispositivos e %s anexos (%s chunk%s).",
                urn,
                len(resultado_llm.get("dispositivos", [])),
                len(resultado_llm.get("anexos", [])),
                chunk_total,
                "" if chunk_total == 1 else "s",
            )

            if args.dry_run:
                print(f"\n=== Texto bruto ({urn}) ===\n{texto}\n")
                print(f"--- Dispositivos LLM ({urn}) ---")
                for linha in _resumir_dispositivos(resultado_llm.get("dispositivos", []), max_itens=None):
                    print(linha)
                print("--- fim ---\n")
                processados += 1
                continue

            json_str = json.dumps(resultado_llm, ensure_ascii=False, indent=2)
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
