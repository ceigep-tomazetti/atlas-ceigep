"""Orquestrador de descoberta de atos normativos."""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from typing import Iterable, Optional

from ..utils import db as db_utils
from ..utils import storage as storage_utils
from .strategies import build_strategy_registry
from .types import FonteDescoberta

import calendar
import hashlib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _default_periodo() -> tuple[date, date]:
    hoje = date.today()
    inicio = hoje.replace(day=1)
    return inicio, hoje


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _month_end(d: date) -> date:
    last_day = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=last_day)


def _previous_month(d: date) -> date:
    if d.month == 1:
        return date(d.year - 1, 12, 1)
    return date(d.year, d.month - 1, 1)


def registrar_execucao(origem_id: str, periodo_inicio: date, periodo_fim: date, *, novos: int, duplicados: int, falhas: int, observacoes: Optional[str] = None) -> None:
    db_utils.registrar_execucao(
        {
            "fonte_origem_id": origem_id,
            "periodo_inicio": periodo_inicio.isoformat() if periodo_inicio else None,
            "periodo_fim": periodo_fim.isoformat() if periodo_fim else None,
            "total_descobertos": novos,
            "total_duplicados": duplicados,
            "total_falhas": falhas,
            "observacoes": observacoes,
            "status": "concluido",
            "finalizado_em": datetime.utcnow().isoformat(),
        }
    )


def inserir_descoberta(descoberta: FonteDescoberta, *, append_only: bool = False) -> bool:
    """Insere ou atualiza um registro de descoberta. Retorna True se for novo."""
    params = descoberta.as_db_params()
    exists = db_utils.find_fonte_documento(params["fonte_origem_id"], params["urn_lexml"])
    payload = {
        **params,
        "status": "descoberto",
        "atualizado_em": datetime.utcnow().isoformat(),
    }
    if exists:
        if append_only:
            logging.debug(
                "Registro %s já existe e append_only ativo. Mantendo dados atuais.",
                params["urn_lexml"],
            )
            return False
        db_utils.update_fonte_documento(params["fonte_origem_id"], params["urn_lexml"], payload)
        return False
    db_utils.insert_fonte_documento(payload)
    return True


def processar_origem(
    origem: dict,
    estrategia,
    periodo_inicio: date,
    periodo_fim: date,
    limite: Optional[int],
    *,
    dry_run: bool,
    append_only: bool,
    ano: Optional[int] = None,
) -> tuple[int, int, int, list[str]]:
    logging.info(
        "Iniciando descoberta para origem %s (%s) período %s → %s",
        origem["nome"],
        origem["id"],
        periodo_inicio,
        periodo_fim,
    )
    novos = duplicados = falhas = 0
    novos_urns: list[str] = []
    try:
        descobertas = estrategia.discover(
            periodo_inicio,
            periodo_fim,
            limite=limite,
            ano=ano,
        )
        for descoberta in descobertas:
            if dry_run:
                logging.info("Encontrado (dry-run): %s", descoberta.urn_lexml)
                continue
            try:
                is_new = inserir_descoberta(descoberta, append_only=append_only)
                if is_new:
                    novos += 1
                    novos_urns.append(descoberta.urn_lexml)
                else:
                    duplicados += 1
            except Exception as exc:  # noqa: BLE001
                falhas += 1
                logging.exception(
                    "Falha ao persistir descoberta %s: %s",
                    descoberta.urn_lexml,
                    exc,
                )
                continue
    except Exception as exc:  # noqa: BLE001
        logging.exception("Erro não tratado na estratégia da origem %s: %s", origem["id"], exc)
        falhas += 1
    logging.info(
        "Origem %s concluída: novos=%s duplicados=%s falhas=%s",
        origem["id"],
        novos,
        duplicados,
        falhas,
    )
    return novos, duplicados, falhas, novos_urns


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Crawler de descoberta de origens legislativas.")
    parser.add_argument("--origin-id", action="append", help="UUID da fonte_origem a processar (pode repetir).")
    parser.add_argument("--since", help="Data inicial (YYYY-MM-DD).")
    parser.add_argument("--until", help="Data final (YYYY-MM-DD).")
    parser.add_argument("--limit", type=int, help="Limite de itens por origem.")
    parser.add_argument(
        "--urn",
        action="append",
        help="URN LexML específica para forçar extração (pode repetir). Ignora --limit para esses itens.",
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Executa descoberta para todos os itens de um ano específico (substitui since/until).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Executa sem gravar dados no banco.")
    parser.add_argument(
        "--append-only",
        action="store_true",
        help="Não atualiza registros existentes; apenas insere novos (útil para backfill).",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Percorre indefinidamente meses anteriores (controlar via interrupção manual).",
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Executa apenas a fase de extração para itens com status 'descoberto'.",
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Executa somente descoberta (não extrai texto bruto).",
    )

    args = parser.parse_args(argv)


    origens = db_utils.fetch_origens(args.origin_id)
    if not origens:
        logging.warning("Nenhuma origem ativa encontrada para os critérios fornecidos.")
        return

    registry = build_strategy_registry(origens)

    urns_param = list(dict.fromkeys(args.urn)) if args.urn else None

    if args.extract:
        run_extract(origens, registry, args.limit, dry_run=args.dry_run, urns=urns_param)
        return

    if args.backfill:
        run_backfill(origens, registry, args.limit, dry_run=args.dry_run, append_only=args.append_only)
        return

    if args.year is not None:
        if args.since or args.until:
            raise SystemExit("Não é permitido combinar --year com --since/--until.")
        try:
            periodo_inicio = date(args.year, 1, 1)
            periodo_fim = date(args.year, 12, 31)
        except ValueError as exc:  # noqa: BLE001
            raise SystemExit(f"Ano inválido: {exc}") from exc
        ano_execucao = args.year
    else:
        ano_execucao = None
        periodo_inicio, periodo_fim = _default_periodo()
        parsed_since = _parse_date(args.since)
        parsed_until = _parse_date(args.until)
        if parsed_since:
            periodo_inicio = parsed_since
        if parsed_until:
            periodo_fim = parsed_until
        if periodo_inicio > periodo_fim:
            raise SystemExit("Período inválido: data inicial maior que data final.")

    novas_descobertas: dict[str, list[str]] = {}

    for origem in origens:
        origem_id = str(origem["id"])
        estrategia = registry.get(origem_id)
        if not estrategia:
            logging.info("Nenhuma estratégia suportando origem %s (%s). Ignorando.", origem["nome"], origem_id)
            continue

        novos, duplicados, falhas, urns_novos = processar_origem(
            origem,
            estrategia,
            periodo_inicio,
            periodo_fim,
            args.limit,
            dry_run=args.dry_run,
            append_only=args.append_only,
            ano=ano_execucao,
        )
        if urns_novos:
            novas_descobertas[origem_id] = urns_novos
        if not args.dry_run:
            registrar_execucao(
                origem_id,
                periodo_inicio,
                periodo_fim,
                novos=novos,
                duplicados=duplicados,
                falhas=falhas,
            )

    if not args.discover_only:
        mapping = novas_descobertas or None
        if mapping:
            run_extract(
                origens,
                registry,
                args.limit,
                dry_run=args.dry_run,
                urns_por_origem=mapping if not args.dry_run else None,
                urns=urns_param,
            )
        else:
            if urns_param:
                run_extract(origens, registry, args.limit, dry_run=args.dry_run, urns=urns_param)
            else:
                logging.info("Nenhuma descoberta nova no período informado – extração ignorada.")


def run_backfill(origens, registry, limite: Optional[int], *, dry_run: bool, append_only: bool) -> None:
    logging.info("Backfill indefinido iniciado. Pressione CTRL+C para interromper.")
    current_month = _month_start(date.today())
    while True:
        periodo_inicio = current_month
        periodo_fim = _month_end(current_month)
        logging.info("Processando período %s → %s", periodo_inicio, periodo_fim)
        novas_descobertas: dict[str, list[str]] = {}
        for origem in origens:
            origem_id = str(origem["id"])
            estrategia = registry.get(origem_id)
            if not estrategia:
                logging.info("Nenhuma estratégia suportando origem %s (%s). Ignorando.", origem["nome"], origem_id)
                continue
            novos, duplicados, falhas, urns_novos = processar_origem(
                origem,
                estrategia,
                periodo_inicio,
                periodo_fim,
                limite,
                dry_run=dry_run,
                append_only=append_only,
                ano=None,
            )
            if urns_novos:
                novas_descobertas[origem_id] = urns_novos
            if not dry_run:
                registrar_execucao(
                    origem_id,
                    periodo_inicio,
                    periodo_fim,
                    novos=novos,
                    duplicados=duplicados,
                    falhas=falhas,
                    observacoes="backfill",
                )
        if not dry_run:
            mapping = novas_descobertas or None
            if mapping:
                run_extract(
                    origens,
                    registry,
                    limite,
                    dry_run=False,
                    urns_por_origem=mapping,
                )
            else:
                logging.info("Backfill não gerou novas descobertas neste ciclo – etapa de extração ignorada.")
        current_month = _previous_month(current_month)


def run_extract(
    origens,
    registry,
    limite: Optional[int],
    *,
    dry_run: bool,
    urns_por_origem: Optional[dict[str, list[str]]] = None,
    urns: Optional[list[str]] = None,
) -> None:
    logging.info("Iniciando fase de extração de textos brutos.")
    urns_global = list(dict.fromkeys(urns or []))
    for origem in origens:
        origem_id = str(origem["id"])
        estrategia = registry.get(origem_id)
        if not estrategia:
            continue
        if not hasattr(estrategia, "extract_text"):
            logging.info("Estratégia da origem %s não implementa extração. Pulando.", origem_id)
            continue
        registros = []
        urns_alvo: list[str] = []
        if urns_por_origem and origem_id in urns_por_origem:
            urns_alvo.extend(urns_por_origem[origem_id])
        if urns_global:
            urns_alvo.extend(urns_global)
        if urns_alvo:
            registros = db_utils.fetch_descobertos_por_urns(origem_id, list(dict.fromkeys(urns_alvo)))
        else:
            registros = db_utils.fetch_descobertos(origem_id, limite)
        if not registros:
            if urns_alvo:
                logging.info(
                    "Nenhum item 'descoberto' correspondente às URNs fornecidas na origem %s.",
                    origem_id,
                )
            else:
                logging.info("Nenhum item 'descoberto' para extrair na origem %s.", origem_id)
            continue

        extraidos = 0
        for registro in registros:
            urn = registro["urn_lexml"]
            try:
                texto = estrategia.extract_text(registro)
            except Exception as exc:  # noqa: BLE001
                logging.exception("Falha ao extrair texto de %s: %s", urn, exc)
                continue

            if not texto:
                logging.warning("Texto vazio ao extrair %s. Mantendo como descoberto.", urn)
                continue

            if dry_run:
                logging.info("Extrairia texto bruto para %s", urn)
                extraidos += 1
                continue

            hash_texto = hashlib.sha256(texto.encode("utf-8")).hexdigest()
            caminho = storage_utils.upload_text(urn, texto)
            db_utils.update_fonte_documento(
                origem_id,
                urn,
                {
                    "caminho_texto_bruto": caminho,
                    "hash_texto_bruto": hash_texto,
                    "texto_extraido_em": datetime.utcnow().isoformat(),
                    "status": "processado",
                },
            )
            extraidos += 1
        logging.info(
            "Extração concluída para origem %s: %s itens processados (dry_run=%s).",
            origem_id,
            extraidos,
            dry_run,
        )


if __name__ == "__main__":
    main()
