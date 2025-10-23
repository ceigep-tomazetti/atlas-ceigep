"""Estratégia de descoberta para a API de legislações da Casa Civil de Goiás."""

from __future__ import annotations

import calendar
import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Generator, Iterable, Optional

from urllib.parse import quote

import requests

from ..types import FonteDescoberta


USER_AGENT = "AtlasDiscoveryBot/0.1 (+https://ceigep-atlas)"


def _first_day(d: date) -> date:
    return d.replace(day=1)


def _last_day(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=last)


def _iterate_months(start: date, end: date) -> Iterable[tuple[date, date]]:
    cursor = date(start.year, start.month, 1)
    limit = date(end.year, end.month, calendar.monthrange(end.year, end.month)[1])
    while cursor <= limit:
        yield _first_day(cursor), _last_day(cursor)
        # avança para o primeiro dia do próximo mês
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


def _slug_tipo(tipo: Optional[str]) -> str:
    if not tipo:
        return "desconhecido"
    normalized = (
        tipo.lower()
        .replace(" ", ".")
        .replace("/", ".")
        .replace("º", "")
        .replace("ª", "")
    )
    return normalized.strip(".")


def _normalize_numero(raw: Optional[str], fallback_date: date) -> str:
    if raw and raw.strip():
        return "".join(ch for ch in raw if ch.isalnum())
    # quando não houver número, usamos o ano como fallback para manter URN válida
    return str(fallback_date.year)


def _build_urn(metadados: dict) -> Optional[str]:
    try:
        data_legislacao = datetime.strptime(
            metadados["data_legislacao"], "%d/%m/%Y"
        ).date()
    except (KeyError, ValueError):
        return None

    tipo_slug = _slug_tipo(metadados.get("tipo_legislacao"))
    numero = _normalize_numero(metadados.get("numero"), data_legislacao)
    return f"br;go;estadual;{tipo_slug};{data_legislacao.isoformat()};{numero}"


@dataclass
class GoiasApiDiscovery:
    """Discovery worker for Casa Civil Goiás open data API."""

    ORIGIN_ID = "fd64e393-159f-4484-9ea4-e9437753791d"

    origem: dict
    session: requests.Session = requests.Session()

    BASE_URL = "https://legisla.casacivil.go.gov.br/api/v2/pesquisa/legislacoes/dados_abertos.json"
    MAX_ITEMS_PER_REQUEST = 1000

    def __post_init__(self) -> None:
        self.session.headers.update({"User-Agent": USER_AGENT})

    @classmethod
    def supports(cls, origem: dict) -> bool:
        return str(origem.get("id")) == cls.ORIGIN_ID

    def discover(
        self,
        periodo_inicio: date,
        periodo_fim: date,
        *,
        limite: Optional[int] = None,
        ano: Optional[int] = None,
    ) -> Generator[FonteDescoberta, None, None]:
        """Percorre a API retornando metadados de atos dentro do período informado."""
        total_emitidos = 0

        if ano is not None:
            params = self._default_params()
            params["ano"] = str(ano)
            params["periodo_inicial_legislacao"] = ""
            params["periodo_final_legislacao"] = ""
            items = self._fetch_items(params, contexto=f"ano {ano}")
            for descoberta in self._descobertas_from_items(items):
                if limite is not None and total_emitidos >= limite:
                    return
                total_emitidos += 1
                yield descoberta
            return

        for inicio, fim in _iterate_months(periodo_inicio, periodo_fim):
            params = self._default_params()
            params["periodo_inicial_legislacao"] = inicio.strftime("%Y-%m-%d")
            params["periodo_final_legislacao"] = fim.strftime("%Y-%m-%d")
            items = self._fetch_items(params, contexto=f"{inicio} → {fim}")

            for descoberta in self._descobertas_from_items(items):
                if limite is not None and total_emitidos >= limite:
                    return
                total_emitidos += 1
                yield descoberta

    def extract_text(self, registro: dict) -> str:
        metadados = registro.get("metadados_brutos")
        if isinstance(metadados, str):
            metadados = json.loads(metadados)
        texto = metadados.get("conteudo_sem_formatacao") or ""
        texto = self._sanitize_text(texto)
        return texto

    def _default_params(self) -> dict:
        return {
            "numero": "",
            "conteudo": "",
            "tipo_legislacao": "",
            "estado_legislacao": "",
            "categoria_legislacao": "",
            "ementa": "",
            "autor": "",
            "ano": "",
            "periodo_inicial_legislacao": "",
            "periodo_final_legislacao": "",
            "periodo_inicial_diario": "",
            "periodo_final_diario": "",
            "termo": "",
            "semantico": "",
        }

    def _resolve_url_fonte(self, item: dict, urn: str) -> str:
        diarios = item.get("diarios") or []
        for diario in diarios:
            url = diario.get("link_download") or diario.get("link")
            if url:
                return url

        candidatos = [
            item.get("url_documento"),
            item.get("url_visualizacao"),
            item.get("url"),
            item.get("link"),
        ]
        for url in candidatos:
            if url:
                return url

        arquivos = item.get("arquivos") or []
        for arquivo in arquivos:
            url = arquivo.get("link") or arquivo.get("url")
            if url:
                return url

        identificador = item.get("nid") or item.get("id")
        if identificador:
            return f"https://legisla.casacivil.go.gov.br/api/v2/legislacoes/{identificador}.json"

        return f"https://legisla.casacivil.go.gov.br/busca?urn={quote(urn)}"

    def _fetch_items(self, params: dict, *, contexto: str) -> list:
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            logging.warning("Erro ao consultar API de Goiás (%s): %s", contexto, exc)
            return []

        try:
            payload = response.json()
        except ValueError as exc:
            logging.warning("Resposta JSON inválida para %s: %s", contexto, exc)
            return []

        if isinstance(payload, dict):
            # a API deve devolver lista, mas em caso de erro documental mantemos referência
            items = payload.get("resultados", [])
        else:
            items = payload

        if items and len(items) >= self.MAX_ITEMS_PER_REQUEST:
            logging.info(
                "Limite da API alcançado (%s itens) para %s; considerar janela menor.",
                len(items),
                contexto,
            )

        return items or []

    def _descobertas_from_items(self, items: Iterable[dict]) -> Generator[FonteDescoberta, None, None]:
        for raw_item in items:
            try:
                item = json.loads(raw_item) if isinstance(raw_item, str) else raw_item
            except json.JSONDecodeError:
                logging.debug("Item ignorado: JSON inválido")
                continue

            urn = _build_urn(item)
            if not urn:
                continue

            url_fonte = self._resolve_url_fonte(item, urn)
            diarios = item.get("diarios") or []
            data_legislacao = self._parse_date(item.get("data_legislacao"))
            data_publicacao = None
            if diarios:
                data_publicacao = self._parse_date(diarios[0].get("data_diario"))

            yield FonteDescoberta(
                fonte_origem_id=str(self.origem["id"]),
                urn_lexml=urn,
                url_fonte=url_fonte,
                tipo_ato=_slug_tipo(item.get("tipo_legislacao")),
                titulo=item.get("titulo"),
                ementa=item.get("ementa"),
                data_legislacao=data_legislacao,
                data_publicacao_diario=data_publicacao,
                orgao_publicador=item.get("autor"),
                metadados_brutos=item,
            )

    @staticmethod
    def _sanitize_text(texto: str) -> str:
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
        texto = re.sub(r"\n{2,}", "\n\n", texto)
        return texto.strip()

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None
