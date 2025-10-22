"""Integração com LLMs (Gemini) para parsing assistido."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai  # type: ignore
except ImportError:  # pragma: no cover - biblioteca opcional
    genai = None


class LLMNotConfigured(RuntimeError):
    """Disparado quando as credenciais/SDK do LLM não estão disponíveis."""


JSON_BLOCK_REGEX = re.compile(r"\{[\s\S]*\}")


@dataclass
class LLMConfig:
    api_key: str
    model: str


def _get_config(model: Optional[str] = None) -> LLMConfig:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise LLMNotConfigured("Defina GEMINI_API_KEY para utilizar o parser assistido por LLM.")
    resolved_model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    return LLMConfig(api_key=api_key, model=resolved_model)


def _build_prompt(texto_bruto: str, registro: Dict[str, Any], heuristicas: Optional[str]) -> str:
    fonte = {
        "urn_lexml": registro.get("urn_lexml"),
        "tipo_ato": registro.get("tipo_ato"),
        "ementa": registro.get("ementa"),
        "data_legislacao": registro.get("data_legislacao"),
        "data_publicacao_diario": registro.get("data_publicacao_diario"),
        "orgao_publicador": registro.get("orgao_publicador"),
    }
    prompt = f"""
Você é um parser jurídico. Analise o texto bruto de um ato normativo e produza um JSON com o seguinte formato:
{{
  "fonte": {{
    "urn_lexml": "...",
    "tipo_ato": "...",
    "titulo": "Lei nº ...",
    "ementa": "...",
    "situacao_vigencia": "vigente"
  }},
  "dispositivos": [
    {{
      "rotulo": "Art. 1º",
      "texto": "... texto completo ...",
      "filhos": [
        {{
          "rotulo": "§ 1º",
          "texto": "...",
          "filhos": [
            {{ "rotulo": "I", "texto": "..." }},
            ...
          ]
        }},
        ...
      ]
    }},
    ...
  ],
  "anexos": [
    {{ "titulo": "Anexo I", "texto": "... texto completo ..." }},
    ...
  ]
}}

Regras importantes:
- Preserve o texto integral de cada dispositivo exatamente como aparece.
- Identifique artigos, parágrafos, incisos e alíneas.
- Se o texto contiver anexos, quadros ou tabelas, mova-os para o array "anexos".
- Se o ato alterar outro texto (ex.: citações entre aspas), inclua o conteúdo na posição correspondente e inclua a chave opcional "tipo": "alteracao".
- Preencha o objeto "fonte" com os metadados disponíveis (título conforme cabeçalho, ementa, situação de vigência, datas, órgão, URL).
- Utilize valores como "vigente", "revogado" ou "desconhecido" para "situacao_vigencia".
- Quando não for possível identificar algum campo, retorne explicitamente o valor JSON `null`.
- Não inclua comentários adicionais. Responda apenas com JSON válido.

Heurísticas atuais do parser determinístico:
{heuristicas or "(heurísticas não fornecidas)"}

Metadados do ato: {json.dumps(fonte, ensure_ascii=False)}

Texto:
\"\"\"{texto_bruto}\"\"\"
"""
    return prompt.strip()


def _extract_first_json_block(text: str) -> str:
    match = JSON_BLOCK_REGEX.search(text)
    if not match:
        raise ValueError("Não foi possível localizar um bloco JSON na resposta do LLM.")
    bloco = match.group(0)
    bloco_limpo = "".join(ch for ch in bloco if ord(ch) >= 32 or ch in "\n\r\t")
    return bloco_limpo


def gerar_estrutura_llm(
    texto_bruto: str,
    registro: Dict[str, Any],
    *,
    heuristicas: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Gera JSON estruturado usando Gemini. Levanta LLMNotConfigured se indisponível."""
    if genai is None:
        raise LLMNotConfigured("Pacote google-generativeai não disponível. Instale para usar o LLM.")

    config = _get_config(model)
    genai.configure(api_key=config.api_key)
    prompt = _build_prompt(texto_bruto, registro, heuristicas)

    modelo = genai.GenerativeModel(config.model)
    resposta = modelo.generate_content(prompt)  # type: ignore[no-untyped-call]
    if resposta.candidates:
        texto_resposta = resposta.candidates[0].content.parts[0].text  # type: ignore[attr-defined]
    else:
        raise RuntimeError("Resposta vazia do LLM.")

    json_str = _extract_first_json_block(texto_resposta)
    return json.loads(json_str)


def gerar_revisao_regex(
    texto_bruto: str,
    saida_deterministica: Dict[str, Any],
    saida_llm: Dict[str, Any],
    *,
    heuristicas: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Solicita ao LLM sugestões de aprimoramento com base nas divergências."""
    if genai is None:
        raise LLMNotConfigured("Pacote google-generativeai não disponível. Instale para usar o LLM.")

    config = _get_config(model)
    genai.configure(api_key=config.api_key)

    prompt = f"""
Você atua como revisor do parser determinístico. Receba o texto bruto de um ato normativo, a saída do parser heurístico (A)
e a saída do parser LLM (B). Compare os dois resultados, identifique divergências relevantes e sugira regras ou melhorias
heurísticas (regex, pré-processamento, divisão de anexos etc.) que ajudem A a se aproximar de B nas próximas execuções.

Não reescreva o JSON resultante; apenas aponte problemas e proponha ajustes.

Heurísticas atuais:
{heuristicas or "(heurísticas não fornecidas)"}

Texto bruto:
{texto_bruto}

Saída heurística (A):
{json.dumps(saida_deterministica, ensure_ascii=False, indent=2)}

Saída LLM (B):
{json.dumps(saida_llm, ensure_ascii=False, indent=2)}

Responda em português. Liste as divergências e sugestões objetivas.
"""

    modelo = genai.GenerativeModel(config.model)
    resposta = modelo.generate_content(prompt)  # type: ignore[no-untyped-call]
    if not resposta.candidates:
        raise RuntimeError("Resposta vazia do LLM na revisão.")
    return resposta.candidates[0].content.parts[0].text  # type: ignore[attr-defined]
