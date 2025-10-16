"""Parser determinístico genérico para atos legislativos."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Callable, Dict, List, Match, Optional, Pattern, Tuple

import textwrap

# Padrões básicos
ARTIGO_REGEX = re.compile(r"(Art\.?\s*\d+[ºo]?(?:-[A-Za-z])?)\s*", re.IGNORECASE)
PARAGRAFO_REGEX = re.compile(r"(§\s*\d+[ºo]?|Parágrafo único\.)\s*", re.IGNORECASE)
INCISO_REGEX = re.compile(r"(?<!\w)([IVXLCDM]+)\s*(?:[-–—]|\.|:)\s*", re.IGNORECASE)
ALINEA_REGEX = re.compile(r"(?<!\w)([a-z])\)\s*")
HEADER_LOOKAHEAD = r"(?=\s+(?:Art\.|§|Seção|Subseção|Cap[íi]tulo|T[íi]tulo|\Z))"
SECAO_REGEX = re.compile(r"(Seção\s+[IVXLCDM]+(?:\s+[\wÁ-Úá-úçÇºª,-]+)*)\s*" + HEADER_LOOKAHEAD, re.IGNORECASE)
SUBSECAO_REGEX = re.compile(
    r"(Subseção\s+[IVXLCDM]+(?:\s+[\wÁ-Úá-úçÇºª,-]+)*)\s*" + HEADER_LOOKAHEAD,
    re.IGNORECASE,
)
CAPITULO_REGEX = re.compile(
    r"(Cap[íi]tulo\s+[IVXLCDM]+(?:\s+[\wÁ-Úá-úçÇºª,-]+)*)\s*" + HEADER_LOOKAHEAD,
    re.IGNORECASE,
)
ALTERACAO_TRIGGER_REGEX = re.compile(
    r"passa(?:m)?\s+a\s+vigorar\s+com\s+as\s+seguintes\s+alterações",
    re.IGNORECASE,
)
ALTERACAO_BLOCO_REGEX = re.compile(
    r"[“\"](?P<conteudo>.+?)[”\"]\s*\(NR\)",
    re.IGNORECASE | re.DOTALL,
)
ANEXO_REGEX = re.compile(
    r"(?im)^(?P<titulo>(?:anexo|quadro|tabela)\s+[^\r\n]*)",
)
ANEXO_FLEX_REGEX = re.compile(
    r"(?:^|\n|\s+)(?P<titulo>(?:ANEXO|QUADRO|TABELA)\s+[^\r\n]*)",
)
MESES = (
    "janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro"
)
FECHO_REGEX = re.compile(
    rf"(?P<fecho>(?:[A-ZÁ-Ú][\wÁ-Úá-úçÇºª.-]*(?:\s+[\wÁ-Úá-úçÇºª.-]+)*)\s*,\s*\d{{1,2}}\s+de\s+(?:{MESES})"
    r"\s+de\s+\d{4}(?:[^A-Za-z0-9].*)?)\s*$",
    re.IGNORECASE,
)
CITACAO_ARTIGO_SUFIXO_REGEX = re.compile(
    r"^[,;:\s]*(?:no|na|nos|nas|do|da|dos|das|ao|aos|à|às|de|deste|desta|destes|destas|neste|nesta|nesse|nessa|pel[ao]s?)\s+"
    r"(?:art\.?|artigo|par[aá]grafo|§|inciso|al[ií]nea|lei|decreto|portaria|resolu[cç][aã]o|constitui[cç][aã]o)",
    re.IGNORECASE,
)
CITACAO_ARTIGO_PREFIXO_TERMINAIS = {
    "no",
    "na",
    "nos",
    "nas",
    "do",
    "da",
    "dos",
    "das",
    "ao",
    "aos",
    "à",
    "às",
    "pelo",
    "pela",
    "pelos",
    "pelas",
    "conforme",
    "segundo",
    "deste",
    "desta",
    "desse",
    "dessa",
    "desses",
    "dessas",
    "neste",
    "nesta",
    "nesse",
    "nessa",
    "e",
    "ou",
}
CITACAO_ARTIGO_PREFIXO_BIGRAMAS = {
    "nos termos",
}
CITACAO_ARTIGO_PREFIXO_DISPOSITIVO_REGEX = re.compile(
    r"(?:§\s*\d+[ºo]?|art\.?|artigo|inciso|al[ií]nea)\s*$",
    re.IGNORECASE,
)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def parse_ato(registro: Dict, texto: str) -> Dict:
    """Gera o JSON estruturado a partir do texto bruto."""
    metadados = registro.get("metadados_brutos")
    if isinstance(metadados, str):
        metadados = json.loads(metadados)

    corpo, anexos = _separar_anexos(texto)
    texto_normalizado = _normalizar(corpo)
    dispositivos = _extrair_dispositivos(texto_normalizado)

    return {
        "gerado_em": _now_iso(),
        "fonte": {
            "urn_lexml": registro.get("urn_lexml"),
            "tipo_ato": registro.get("tipo_ato"),
            "titulo": registro.get("titulo"),
            "ementa": registro.get("ementa"),
            "data_legislacao": registro.get("data_legislacao"),
            "data_publicacao_diario": registro.get("data_publicacao_diario"),
            "orgao_publicador": registro.get("orgao_publicador"),
            "url_fonte": registro.get("url_fonte"),
        },
        "metadados_origem": metadados,
        "texto_bruto": texto_normalizado,
        "dispositivos": dispositivos,
        "anexos": anexos,
    }


def _normalizar(texto: str) -> str:
    texto = texto.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    texto = texto.replace("...", " ")
    return texto.strip()


def _dividir_titulo_anexo(linha: str) -> Tuple[str, str]:
    linha = linha.strip()
    if not linha:
        return "", ""
    partes = linha.split()
    titulo_tokens = [partes[0]]
    if len(partes) >= 2:
        segundo = partes[1]
        segundo_limpo = segundo.rstrip(":-")
        if re.fullmatch(r"[IVXLCDM]+", segundo_limpo, flags=re.IGNORECASE):
            titulo_tokens.append(segundo_limpo)
        elif re.fullmatch(r"\d+[ºª]?", segundo_limpo):
            titulo_tokens.append(segundo_limpo)
        elif segundo_limpo.lower() in {"único", "unico"}:
            titulo_tokens.append(segundo_limpo)
    titulo = " ".join(titulo_tokens)
    resto = linha[len(titulo):].strip()
    return titulo, resto


def _separar_anexos(texto: str) -> Tuple[str, List[Dict]]:
    """Retorna corpo principal e lista de anexos (ex.: ANEXO, QUADRO, TABELA)."""
    marcadores = [
        {"start": match.start("titulo"), "linha": match.group("titulo")}
        for match in ANEXO_REGEX.finditer(texto)
    ]
    if not marcadores:
        for match in ANEXO_FLEX_REGEX.finditer(texto):
            titulo = match.group("titulo")
            if not titulo:
                continue
            inicio = match.start("titulo")
            marcadores.append({"start": inicio, "linha": titulo})

    if not marcadores:
        return texto, []

    marcadores.sort(key=lambda item: item["start"])
    corpo = texto[: marcadores[0]["start"]].rstrip()
    anexos: List[Dict] = []
    for idx, info in enumerate(marcadores):
        inicio = info["start"]
        end = marcadores[idx + 1]["start"] if idx + 1 < len(marcadores) else len(texto)
        bloco = texto[inicio:end].lstrip()
        if not bloco:
            continue
        linha_bruta, sep, restante = bloco.partition("\n")
        titulo, resto_linha = _dividir_titulo_anexo(linha_bruta)
        if not titulo:
            titulo = linha_bruta.strip()
        partes_conteudo = []
        if resto_linha:
            partes_conteudo.append(resto_linha.strip())
        if sep:
            partes_conteudo.append(restante.strip())
        conteudo = "\n".join(parte for parte in partes_conteudo if parte)
        anexos.append({"titulo": titulo, "texto": conteudo})

    return corpo, anexos


def _ordenar_marcos_superiores(texto: str) -> List[Tuple[str, Match]]:
    """Retorna matches de artigos/seções em ordem de aparição."""
    candidatos: List[Tuple[str, Match]] = []
    for tipo, regex in (
        ("artigo", ARTIGO_REGEX),
        ("subsecao", SUBSECAO_REGEX),
        ("secao", SECAO_REGEX),
        ("capitulo", CAPITULO_REGEX),
    ):
        for match in regex.finditer(texto):
            if tipo == "artigo" and _artigo_parece_citacao(texto, match):
                continue
            candidatos.append((tipo, match))

    if not candidatos:
        return []

    candidatos.sort(key=lambda item: item[1].start())

    resultado: List[Tuple[str, Match]] = []
    for tipo, match in candidatos:
        if resultado:
            ultimo_tipo, ultimo_match = resultado[-1]
            if match.start() == ultimo_match.start() and match.end() == ultimo_match.end():
                prioridade = {"artigo": 4, "subsecao": 3, "secao": 2, "capitulo": 1}
                if prioridade.get(tipo, 0) > prioridade.get(ultimo_tipo, 0):
                    resultado[-1] = (tipo, match)
                continue
        resultado.append((tipo, match))
    return resultado


def _artigo_parece_citacao(texto: str, match: Match) -> bool:
    """Heurística para diferenciar citações de artigos reais."""
    inicio, fim = match.span()
    prefixo = texto[max(0, inicio - 40) : inicio]
    sufixo = texto[fim : fim + 60]
    prefixo_normalizado = prefixo.replace("\u00a0", " ")
    sufixo_normalizado = sufixo.replace("\u00a0", " ")

    # Palavras imediatamente anteriores que indicam referência a outro dispositivo
    tokens_prefixo = re.findall(r"\b[\w§º]+\b", prefixo_normalizado.lower())
    if tokens_prefixo:
        ultimo = tokens_prefixo[-1]
        if ultimo in CITACAO_ARTIGO_PREFIXO_TERMINAIS:
            return True
        if len(tokens_prefixo) >= 2:
            penultimo = tokens_prefixo[-2]
            if penultimo in CITACAO_ARTIGO_PREFIXO_TERMINAIS:
                return True
            if " ".join((penultimo, ultimo)) in CITACAO_ARTIGO_PREFIXO_BIGRAMAS:
                return True

    if CITACAO_ARTIGO_PREFIXO_DISPOSITIVO_REGEX.search(prefixo_normalizado):
        return True

    sufixo_reduzido = sufixo_normalizado.lstrip(" ,;:-")
    if CITACAO_ARTIGO_SUFIXO_REGEX.match(sufixo_reduzido):
        return True

    return False


def _paragrafo_elegivel(match: Match) -> bool:
    return not _paragrafo_parece_citacao(match.string, match)


def _paragrafo_parece_citacao(texto: str, match: Match) -> bool:
    inicio, fim = match.span()
    prefixo = texto[max(0, inicio - 40) : inicio]
    sufixo = texto[fim : fim + 60]
    prefixo_normalizado = prefixo.replace("\u00a0", " ")
    sufixo_normalizado = sufixo.replace("\u00a0", " ")

    tokens_prefixo = re.findall(r"\b[\w§º]+\b", prefixo_normalizado.lower())
    if tokens_prefixo:
        ultimo = tokens_prefixo[-1]
        if ultimo in CITACAO_ARTIGO_PREFIXO_TERMINAIS:
            return True
        if len(tokens_prefixo) >= 2:
            penultimo = tokens_prefixo[-2]
            if penultimo in CITACAO_ARTIGO_PREFIXO_TERMINAIS:
                return True
            if " ".join((penultimo, ultimo)) in CITACAO_ARTIGO_PREFIXO_BIGRAMAS:
                return True

    if CITACAO_ARTIGO_PREFIXO_DISPOSITIVO_REGEX.search(prefixo_normalizado):
        return True

    sufixo_reduzido = sufixo_normalizado.lstrip(" ,;:-")
    if CITACAO_ARTIGO_SUFIXO_REGEX.match(sufixo_reduzido):
        return True

    return False


def _identificar_rotulo_alteracao(texto: str) -> Optional[str]:
    artigo = ARTIGO_REGEX.search(texto)
    if artigo:
        return _formata_artigo(artigo.group(1))
    for regex in (SUBSECAO_REGEX, SECAO_REGEX, CAPITULO_REGEX):
        match = regex.search(texto)
        if match:
            return match.group(1).strip()
    return None


def _extrair_blocos_alteracao(corpo: str) -> Tuple[str, List[Dict]]:
    """Remove blocos '“...” (NR)' e retorna texto residual + filhos de alteração."""
    filhos: List[Dict] = []
    partes_texto: List[str] = []
    cursor = 0

    for match in ALTERACAO_BLOCO_REGEX.finditer(corpo):
        inicio, fim = match.span()
        if inicio > cursor:
            trecho = corpo[cursor:inicio].strip()
            if trecho:
                partes_texto.append(trecho)
        bloco = (match.group("conteudo") or "").strip()
        if bloco:
            rotulo = _identificar_rotulo_alteracao(bloco) or f"alteracao_{len(filhos) + 1}"
            filho = {"rotulo": rotulo, "texto": bloco, "tipo": "alteracao"}
            sub_dispositivos = _extrair_dispositivos(bloco, considerar_preambulo=False)
            if sub_dispositivos:
                for idx, sub in enumerate(sub_dispositivos, start=1):
                    sub["ordem"] = idx
                filho["filhos"] = sub_dispositivos
            filhos.append(filho)
        cursor = fim

    if cursor < len(corpo):
        resto = corpo[cursor:].strip()
        if resto:
            partes_texto.append(resto)

    texto_residual = " ".join(partes_texto).strip()
    return texto_residual, filhos


def _processar_corpo_artigo(corpo: str) -> Tuple[str, List[Dict]]:
    """Retorna texto-base do artigo e filhos detectados."""
    filhos: List[Dict] = []
    texto_residual = corpo.strip()

    if ALTERACAO_TRIGGER_REGEX.search(corpo) and ALTERACAO_BLOCO_REGEX.search(corpo):
        texto_residual, filhos_alteracao = _extrair_blocos_alteracao(corpo)
        filhos.extend(filhos_alteracao)

    filhos_normais = _parse_paragrafos_ou_incisos(texto_residual)
    if filhos_normais:
        filhos = filhos_normais + filhos

    for idx, filho in enumerate(filhos, start=1):
        filho["ordem"] = idx

    texto_base = texto_residual.strip()
    if filhos:
        texto_base = _remover_textos_filhos(texto_base, filhos)

    return texto_base, filhos


def _remover_textos_filhos(texto: str, filhos: List[Dict]) -> str:
    resultado = texto
    for filho in filhos:
        trecho = filho.get("_texto_original") or filho.get("texto")
        if not trecho:
            continue
        resultado = _remover_primeira_ocorrencia(resultado, trecho)
    _limpar_marcadores_texto(filhos)
    return resultado.strip()


def _remover_primeira_ocorrencia(texto: str, trecho: str) -> str:
    if not trecho:
        return texto
    indice = texto.find(trecho)
    if indice == -1:
        return texto
    prefixo = texto[:indice].rstrip()
    sufixo = texto[indice + len(trecho) :].lstrip()
    if prefixo and sufixo:
        return f"{prefixo} {sufixo}".strip()
    return ((prefixo or "") + (sufixo or "")).strip()


def _limpar_marcadores_texto(filhos: List[Dict]) -> None:
    for filho in filhos:
        filho.pop("_texto_original", None)
        sub_filhos = filho.get("filhos")
        if isinstance(sub_filhos, list):
            _limpar_marcadores_texto(sub_filhos)


def _separar_fecho(texto: str) -> Tuple[str, Optional[str]]:
    """Isola o fecho (assinaturas/local/data) do restante do texto."""
    match = FECHO_REGEX.search(texto)
    if not match:
        return texto, None
    inicio = match.start("fecho")
    trecho_principal = texto[:inicio].strip()
    fecho = match.group("fecho").strip()
    return trecho_principal, fecho


def _extrair_dispositivos(texto: str, *, considerar_preambulo: bool = True) -> List[Dict]:
    marcadores = _ordenar_marcos_superiores(texto)
    dispositivos: List[Dict] = []

    if not marcadores:
        return [
            {
                "ordem": 0,
                "rotulo": "texto_integral",
                "texto": texto.strip(),
            }
        ]

    if considerar_preambulo:
        primeiro_inicio = marcadores[0][1].start()
        trecho_inicial = texto[:primeiro_inicio].strip()
        if trecho_inicial:
            dispositivos.append({"rotulo": "preambulo", "texto": trecho_inicial})

        primeiro_tipo, primeiro_match = marcadores[0]
        if primeiro_tipo == "artigo":
            numero_primeiro = _numero_artigo(primeiro_match.group(1))
            if numero_primeiro not in (0, 1) and len(marcadores) > 1:
                bloco_fim = marcadores[1][1].start()
                bloco_primeiro = texto[primeiro_match.start():bloco_fim].strip()
                if bloco_primeiro:
                    if dispositivos and dispositivos[0]["rotulo"] == "preambulo":
                        dispositivos[0]["texto"] = f"{dispositivos[0]['texto']} {bloco_primeiro}".strip()
                    else:
                        dispositivos.append({"rotulo": "preambulo", "texto": bloco_primeiro})
                marcadores = marcadores[1:]

    for idx_match, (tipo, match) in enumerate(marcadores):
        start = match.end()
        end = marcadores[idx_match + 1][1].start() if idx_match + 1 < len(marcadores) else len(texto)
        corpo = texto[start:end].strip()

        if tipo == "artigo":
            rotulo = _formata_artigo(match.group(1))
            texto_corpo, filhos = _processar_corpo_artigo(corpo)
            dispositivo = {"rotulo": rotulo, "texto": texto_corpo}
            if filhos:
                dispositivo["filhos"] = filhos
            dispositivos.append(dispositivo)
        else:
            rotulo = match.group(1).strip()
            texto_dispositivo = match.group(0).strip()
            if corpo and not texto_dispositivo.endswith(corpo):
                texto_dispositivo = f"{texto_dispositivo} {corpo}".strip()
            dispositivos.append({"rotulo": rotulo, "texto": texto_dispositivo, "tipo": tipo})

    _ajustar_fecho_final(dispositivos)
    _atribuir_ordens(dispositivos)
    return dispositivos


def _parse_paragrafos_ou_incisos(texto: str) -> List[Dict]:
    paragrafos = _split_sections(texto, PARAGRAFO_REGEX, filtro=_paragrafo_elegivel)
    if paragrafos:
        filhos = []
        for ordem, (rotulo_bruto, conteudo, cabecalho) in enumerate(paragrafos, start=1):
            rotulo = rotulo_bruto
            texto_original = f"{cabecalho} {conteudo}".strip() if conteudo else cabecalho
            texto_limpo = conteudo.strip()
            filho = {"ordem": ordem, "rotulo": rotulo, "texto": texto_limpo, "_texto_original": texto_original}
            incisos = _split_sections(conteudo, INCISO_REGEX)
            if incisos:
                filho["filhos"] = _montar_incisos(incisos)
                filho["texto"] = _remover_textos_filhos(filho["texto"], filho["filhos"])
            filhos.append(filho)
        return filhos

    incisos = _split_sections(texto, INCISO_REGEX)
    if incisos:
        return _montar_incisos(incisos)

    return []


def _montar_incisos(sections: List[Tuple[str, str, str]]) -> List[Dict]:
    dispositivos = []
    for ordem, (rotulo_bruto, conteudo, cabecalho) in enumerate(sections, start=1):
        rotulo = rotulo_bruto.rstrip(".-–—:")
        texto_original = f"{cabecalho} {conteudo}".strip() if conteudo else cabecalho
        texto_limpo = conteudo.strip()
        dispositivo = {"ordem": ordem, "rotulo": rotulo, "texto": texto_limpo, "_texto_original": texto_original}
        alineas = _split_sections(conteudo, ALINEA_REGEX)
        if alineas:
            dispositivo["filhos"] = [
                {
                    "ordem": idx + 1,
                    "rotulo": rotulo_alinea.rstrip(")"),
                    "texto": texto_alinea.strip(),
                    "_texto_original": f"{cabecalho_alinea} {texto_alinea}".strip() if texto_alinea else cabecalho_alinea,
                }
                for idx, (rotulo_alinea, texto_alinea, cabecalho_alinea) in enumerate(alineas)
            ]
            dispositivo["texto"] = _remover_textos_filhos(dispositivo["texto"], dispositivo["filhos"])
        dispositivos.append(dispositivo)
    return dispositivos


def _split_sections(
    texto: str,
    padrao: Pattern,
    filtro: Optional[Callable[[Match], bool]] = None,
) -> List[Tuple[str, str, str]]:
    matches = [match for match in padrao.finditer(texto) if filtro is None or filtro(match)]
    if not matches:
        return []

    sections = []
    for idx, match in enumerate(matches):
        rotulo = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(texto)
        conteudo = texto[start:end].strip()
        cabecalho_original = match.group(0).strip()
        sections.append((rotulo, conteudo, cabecalho_original))
    return sections


def _remover_prefixo_rotulo(texto: str, rotulo: str) -> str:
    texto = texto.strip()
    if texto.startswith(rotulo):
        return texto[len(rotulo):].strip()
    if texto.startswith(f"{rotulo}."):
        return texto[len(rotulo) + 1 :].strip()
    return texto


def _ajustar_fecho_final(dispositivos: List[Dict]) -> None:
    if not dispositivos or any(d.get("rotulo") == "disposicao_final" for d in dispositivos):
        return

    for dispositivo in reversed(dispositivos):
        rotulo = dispositivo.get("rotulo", "")
        if rotulo in {"preambulo", "texto_integral"}:
            continue

        texto = dispositivo.get("texto", "")
        corpo = texto
        if rotulo.lower().startswith("art"):
            corpo = _remover_prefixo_rotulo(texto, rotulo)

        corpo_limpo, fecho = _separar_fecho(corpo)
        if fecho:
            if rotulo.lower().startswith("art"):
                dispositivo["texto"] = f"{rotulo} {corpo_limpo}".strip() if corpo_limpo else rotulo
            else:
                dispositivo["texto"] = corpo_limpo or texto
            dispositivos.append({"rotulo": "disposicao_final", "texto": fecho})
        break


def _atribuir_ordens(dispositivos: List[Dict]) -> None:
    ordem_corrente = 0
    for dispositivo in dispositivos:
        rotulo = dispositivo.get("rotulo")
        if rotulo in {"preambulo", "texto_integral"}:
            dispositivo["ordem"] = 0
        else:
            ordem_corrente += 1
            dispositivo["ordem"] = ordem_corrente


def _numero_artigo(rotulo: str) -> int:
    numeros = re.findall(r"\d+", rotulo)
    if not numeros:
        return 0
    try:
        return int(numeros[0])
    except ValueError:
        return 0


def _formata_artigo(rotulo: str) -> str:
    rotulo = rotulo.strip()
    if rotulo.lower().startswith("art"):
        resto = rotulo.split(" ", 1)[1] if " " in rotulo else rotulo[3:]
        return f"Art. {resto.strip()}"
    return rotulo


def resumir_dispositivos(dispositivos: List[Dict], max_itens: Optional[int] = 5) -> List[str]:
    """Cria linhas resumidas para debug em terminal."""
    linhas: List[str] = []
    dispositivos_iter = dispositivos if max_itens is None else dispositivos[:max_itens]
    for dispositivo in dispositivos_iter:
        linhas.append(_formatar_linha(dispositivo["rotulo"], dispositivo["texto"]))
        filhos = dispositivo.get("filhos", [])
        filhos_iter = filhos if max_itens is None else filhos[:max_itens]
        for filho in filhos_iter:
            linhas.append("  * " + _formatar_linha(filho["rotulo"], filho["texto"]))
            netos = filho.get("filhos", [])
            netos_iter = netos if max_itens is None else netos[:max_itens]
            for neto in netos_iter:
                linhas.append("    - " + _formatar_linha(neto["rotulo"], neto["texto"]))
    return linhas


def _formatar_linha(rotulo: str, texto: str) -> str:
    resumo = texto.replace("\n", " ")
    return f"{rotulo}: {resumo}"


def describe_heuristics() -> str:
    """Retorna uma descrição textual das regex/heurísticas atuais."""
    return textwrap.dedent(
        f"""
        Regex utilizadas pelo parser determinístico:
        - ARTIGO_REGEX: {ARTIGO_REGEX.pattern}
        - PARAGRAFO_REGEX: {PARAGRAFO_REGEX.pattern}
        - INCISO_REGEX: {INCISO_REGEX.pattern}
        - ALINEA_REGEX: {ALINEA_REGEX.pattern}
        - SECAO_REGEX: {SECAO_REGEX.pattern}
        - SUBSECAO_REGEX: {SUBSECAO_REGEX.pattern}
        - CAPITULO_REGEX: {CAPITULO_REGEX.pattern}
        - ALTERACAO_TRIGGER_REGEX: {ALTERACAO_TRIGGER_REGEX.pattern}
        - ALTERACAO_BLOCO_REGEX: {ALTERACAO_BLOCO_REGEX.pattern}
        - FECHO_REGEX: {FECHO_REGEX.pattern}
        Regras atuais: dividir preâmbulo antes do primeiro artigo; se o primeiro artigo não é o 'Art. 1º', tratá-lo como parte do preâmbulo; identificar parágrafos/incisos/alíneas via regex; detectar blocos de alteração introduzidos por 'passa a vigorar...' mantendo-os como filhos do artigo com tipo 'alteracao'; reconhecer seções/subseções/capítulos como dispositivos autônomos; isolar o fecho (cidade/data/assinaturas) em 'disposicao_final'; atribuir ordens preservando o preâmbulo como 0.
        """
    ).strip()
