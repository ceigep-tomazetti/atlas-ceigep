"""CLI para carregar atos normativos estruturados para o esquema relacional."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from ..utils import db as db_utils
from ..utils import storage as storage_utils
from .repository import NormativeRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


TIPOS_VALIDOS = {
    "titulo",
    "livro",
    "parte",
    "capitulo",
    "secao",
    "subsecao",
    "artigo",
    "paragrafo",
    "paragrafo_unico",
    "inciso",
    "alinea",
    "item",
    "dispositivo_auxiliar",
}


def _inferir_tipo(dispositivo: Dict) -> str:
    tipo = dispositivo.get("tipo")
    if isinstance(tipo, str) and tipo in TIPOS_VALIDOS:
        return tipo

    id_lexml = (dispositivo.get("id_lexml") or "").lower()
    if id_lexml.startswith("art"):
        return "artigo"
    if id_lexml.endswith("pu"):
        return "paragrafo_unico"
    if "p" in id_lexml and id_lexml.startswith("art"):
        return "paragrafo"
    if "inc" in id_lexml:
        return "inciso"
    if "ali" in id_lexml:
        return "alinea"
    if "item" in id_lexml:
        return "item"
    if id_lexml.startswith("cap"):
        return "capitulo"
    if id_lexml.startswith("sec") and not id_lexml.startswith("subsec"):
        return "secao"
    if id_lexml.startswith("subsec"):
        return "subsecao"
    if id_lexml.startswith("tit"):
        return "titulo"
    if id_lexml.startswith("liv"):
        return "livro"
    if id_lexml.startswith("par") and not id_lexml.startswith("art"):
        return "parte"
    return "dispositivo_auxiliar"


def _hash_texto(texto: Optional[str]) -> Optional[str]:
    if texto is None:
        return None
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _build_relacao_payload(relacao: Dict, dispositivo_id: Optional[str]) -> Optional[Dict]:
    tipo = relacao.get("tipo")
    if not tipo:
        return None

    alvo = relacao.get("alvo") or {}
    urn_alvo = alvo.get("urn") or relacao.get("urn") or relacao.get("urn_alvo")

    descricao = relacao.get("descricao") or relacao.get("texto")
    if not descricao:
        partes = []
        for chave, rotulo in [
            ("tipo_ato", "tipo"),
            ("numero", "nº"),
            ("data", "data"),
            ("dispositivo", "dispositivo"),
        ]:
            valor = alvo.get(chave)
            if valor:
                if rotulo == "nº":
                    partes.append(f"{rotulo} {valor}")
                else:
                    partes.append(f"{rotulo}: {valor}")
        if partes:
            descricao = ", ".join(partes)

    payload = {
        "dispositivo_origem_id": dispositivo_id,
        "dispositivo_alvo_id": relacao.get("dispositivo_alvo_id"),
        "urn_alvo": urn_alvo,
        "tipo": tipo,
        "descricao": descricao,
    }
    return payload


def _registrar_dispositivos(
    repo: NormativeRepository,
    ato_id: str,
    dispositivos: List[Dict],
    *,
    parent_id: Optional[str] = None,
    sequencia: List[int],
    ids_em_uso: Dict[str, int],
    rotulo_index: Dict[str, List[str]],
) -> None:
    for ordem, dispositivo in enumerate(dispositivos, start=1):
        sequencia[0] += 1
        base_id = dispositivo.get("id_lexml") or f"auto_{sequencia[0]}"
        duplicidade = ids_em_uso.get(base_id, 0)
        if duplicidade:
            novo_id = f"{base_id}__{duplicidade+1}"
            logging.warning(
                "Duplicidade de id_lexml '%s' no ato %s. Ajustando para '%s'.",
                base_id,
                ato_id,
                novo_id,
            )
            id_lexml = novo_id
        else:
            id_lexml = base_id
        ids_em_uso[base_id] = duplicidade + 1
        texto = dispositivo.get("texto", "")
        tipo = _inferir_tipo(dispositivo)
        atributos = dispositivo.get("atributos", {})

        dispositivo_id = repo.inserir_dispositivo(
            ato_id=ato_id,
            parent_id=parent_id,
            id_lexml=id_lexml,
            tipo=tipo,
            rotulo=dispositivo.get("rotulo"),
            texto=texto,
            ordem=ordem,
            atributos=atributos,
            hash_texto=_hash_texto(texto),
        )

        rotulo_chave = (dispositivo.get("rotulo") or "").strip().lower()
        if rotulo_chave:
            rotulo_index.setdefault(rotulo_chave, []).append(dispositivo_id)

        for versao in dispositivo.get("versoes", []) or []:
            texto_versao = versao.get("texto", texto)
            versao_payload = {
                "hash_texto": versao.get("hash_texto") or _hash_texto(texto_versao),
                "texto": texto_versao,
                "vigencia_inicio": versao.get("vigencia_inicio"),
                "vigencia_fim": versao.get("vigencia_fim"),
                "origem_alteracao": versao.get("origem_alteracao"),
                "status_vigencia": versao.get("status_vigencia"),
                "anotacoes": versao.get("anotacoes", {}),
            }
            repo.inserir_versao_textual(dispositivo_id, versao_payload)

        for relacao in dispositivo.get("relacoes", []) or []:
            relacao_payload = _build_relacao_payload(relacao, dispositivo_id)
            if relacao_payload:
                repo.inserir_relacao(ato_id, relacao_payload)

        filhos = dispositivo.get("filhos")
        if isinstance(filhos, list) and filhos:
            _registrar_dispositivos(
                repo,
                ato_id,
                filhos,
                parent_id=dispositivo_id,
                sequencia=sequencia,
                ids_em_uso=ids_em_uso,
                rotulo_index=rotulo_index,
            )


def _registrar_anexos(repo: NormativeRepository, ato_id: str, anexos: List[Dict]) -> None:
    for ordem, anexo in enumerate(anexos, start=1):
        texto = anexo.get("texto", "")
        repo.inserir_anexo(
            ato_id=ato_id,
            id_lexml=anexo.get("id_lexml"),
            titulo=anexo.get("titulo"),
            texto=texto,
            ordem=ordem,
            hash_texto=_hash_texto(texto),
        )


def carregar_ato(
    repo: NormativeRepository,
    registro: Dict,
    *,
    dry_run: bool = False,
) -> Tuple[bool, Optional[str]]:
    urn = registro["urn_lexml"]
    caminho_json = registro.get("caminho_parser_json")
    if not caminho_json:
        logging.warning("Registro %s sem caminho_parser_json. Pulando.", urn)
        return False, None

    try:
        conteudo = storage_utils.download_text(caminho_json)
    except Exception as exc:  # noqa: BLE001
        logging.exception("Falha ao baixar JSON estruturado de %s: %s", urn, exc)
        return False, None

    try:
        estrutura = json.loads(conteudo)
    except json.JSONDecodeError as exc:
        logging.exception("JSON inválido para %s: %s", urn, exc)
        return False, None

    hash_json = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()

    if dry_run:
        dispositivos = len(estrutura.get("dispositivos", []) or [])
        anexos = len(estrutura.get("anexos", []) or [])
        logging.info(
            "Carregaria ato %s (hash %s, dispositivos=%s, anexos=%s)",
            urn,
            hash_json,
            dispositivos,
            anexos,
        )
        return True, hash_json

    ato_id = repo.upsert_ato(registro, estrutura, hash_json)
    repo.limpar_componentes(ato_id)

    rotulo_index: Dict[str, List[str]] = {}
    _registrar_dispositivos(
        repo,
        ato_id,
        estrutura.get("dispositivos", []) or [],
        parent_id=None,
        sequencia=[0],
        ids_em_uso={},
        rotulo_index=rotulo_index,
    )
    _registrar_anexos(repo, ato_id, estrutura.get("anexos", []) or [])

    for relacao in estrutura.get("relacoes", []) or []:
        rotulo_origem = (relacao.get("dispositivo_origem_rotulo") or "").strip().lower()
        dispositivo_id = None
        if rotulo_origem:
            ids = rotulo_index.get(rotulo_origem)
            if ids:
                dispositivo_id = ids[0]
        relacao_payload = _build_relacao_payload(relacao, dispositivo_id)
        if relacao_payload:
            repo.inserir_relacao(ato_id, relacao_payload)

    return True, hash_json


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Loader relacional para atos normativos")
    parser.add_argument("--origin-id", action="append", help="UUID da fonte_origem (pode repetir)")
    parser.add_argument("--limit", type=int, help="Limite de itens por origem")
    parser.add_argument("--dry-run", action="store_true", help="Simula execução sem gravar")

    args = parser.parse_args(argv)

    origens = db_utils.fetch_origens(args.origin_id)
    if not origens:
        logging.warning("Nenhuma origem ativa encontrada para os critérios fornecidos.")
        return

    repo = NormativeRepository()
    processados = 0

    for origem in origens:
        origem_id = str(origem["id"])
        registros = repo.fetch_para_normalizacao(origem_id, args.limit)
        if not registros:
            logging.info("Nenhum item pendente de normalização na origem %s.", origem_id)
            continue

        for registro in registros:
            urn = registro["urn_lexml"]
            logging.info("Processando normalização de %s", urn)
            ok, hash_json = carregar_ato(repo, registro, dry_run=args.dry_run)
            if ok:
                processados += 1
                if not args.dry_run:
                    updated_registro = dict(registro)
                    updated_registro["status_parsing"] = registro.get("status_parsing")
                    updated_registro["status_normalizacao"] = "processado"
                    repo.marcar_normalizado(updated_registro)

    logging.info(
        "Normalização concluída: %s itens%s",
        processados,
        " (dry-run)" if args.dry_run else "",
    )


if __name__ == "__main__":
    main()
