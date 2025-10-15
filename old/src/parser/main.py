"""
Módulo principal do Parser - Orquestrador do Pipeline de Parsing.

Este script implementa a lógica "Segmentar e Conquistar" para transformar
o texto bruto de um ato normativo em uma estrutura JSON aninhada e validada.
"""
import logging
import time
import argparse
import json
from pathlib import Path
from typing import Dict, Any

# Módulos do projeto
from .schemas import ParserInput, ParserOutput, Documento, Anexo, Metadados, Timestamps, Cabecalho
from .core.normalizer import normalize_text
from .core.segmenter import segment_by_regex
from .core.article_splitter import split_body_into_articles
from .core.article_parser_fsm import ArticleParserFSM
from ..preprocessor.main import ai_segment_document, ai_parse_article_structure

VERSION = "1.0.0-fsm"

def parse_document(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orquestra o pipeline de parsing completo para um único documento.

    Args:
        payload: Um dicionário contendo os dados de entrada (id, rotulo, texto_bruto).

    Returns:
        Um dicionário representando o objeto ParserOutput.
    """
    t0 = time.time()
    input_data = ParserInput.parse_obj(payload)
    
    metadados_coletados = {"heuristicas": [], "erros": []}

    # 1. Normalização
    texto_normalizado = normalize_text(input_data.texto_bruto)

    # 2. Segmentação (Corpo vs. Anexos)
    blocos = ai_segment_document(texto_normalizado)
    if not blocos:
        logging.info("Fallback para segmentação por regex.")
        metadados_coletados["heuristicas"].append("fallback_anexo_regex")
        blocos = segment_by_regex(texto_normalizado)

    corpo_txt = "".join(
        texto_normalizado[b['start']:b['end']] for b in blocos if b['tipo'] == 'corpo'
    )
    anexos_objs = [
        Anexo(
            rotulo=b.get('rotulo', 'Anexo'),
            conteudo=texto_normalizado[b['start']:b['end']]
        ) for b in blocos if b['tipo'] == 'anexo'
    ]

    # 3. Divisão do Corpo em Artigos
    split_result = split_body_into_articles(corpo_txt)
    header_span = split_result['header_span']
    article_spans = split_result['article_spans']

    cabecalho_obj = Cabecalho(ementa=corpo_txt[header_span['start']:header_span['end']].strip())
    
    # 4. Parsing de cada Artigo
    artigos_objs = []
    for span in article_spans:
        artigo_txt = corpo_txt[span['start']:span['end']]
        parser_fsm = ArticleParserFSM(
            artigo_numero=span['numero'],
            artigo_rotulo=span['rotulo'],
            artigo_texto=artigo_txt
        )
        parsed_artigo = parser_fsm.parse()

        if parsed_artigo["confianca"] < 0.7: # Limiar para fallback
            metadados_coletados["heuristicas"].append(f"fallback_artigo_llm_conf_{parsed_artigo['confianca']:.2f}")
            # TODO: Chamar ai_parse_article_structure e usar o resultado se for melhor
            pass
        
        if parsed_artigo.get("json"):
            artigos_objs.append(parsed_artigo["json"])
        if parsed_artigo.get("erros"):
            metadados_coletados["erros"].extend(parsed_artigo["erros"])

    # 5. Montagem da Saída
    documento_obj = Documento(
        id=input_data.id_documento,
        rotulo=input_data.rotulo,
        cabecalho=cabecalho_obj,
        corpo=artigos_objs
        # TODO: Detectar disposições finais, assinaturas, etc.
    )

    metadados_obj = Metadados(
        timestamps=Timestamps(inicio_ms=t0, fim_ms=time.time()),
        versao_parser=VERSION,
        heuristicas=metadados_coletados["heuristicas"],
        erros=metadados_coletados["erros"]
    )

    output = ParserOutput(
        documento=documento_obj,
        anexos=anexos_objs,
        metadados=metadados_obj
    )

    return output.dict()

def main_cli():
    """
    Ponto de entrada para a execução do parser via linha de comando.
    Lê um manifesto, processa o documento e salva a saída estruturada.
    """
    parser = argparse.ArgumentParser(description='Parser de Atos Normativos - Arquitetura "Segmentar e Conquistar"')
    parser.add_argument('--manifest', required=True, type=Path, help='Caminho para o arquivo de manifesto JSON.')
    parser.add_argument('--outdir', required=True, type=Path, help='Diretório para salvar o arquivo de saída JSON.')
    args = parser.parse_args()

    logging.info(f"Iniciando parsing para o manifesto: {args.manifest}")

    # Carrega os dados do manifesto
    with open(args.manifest, 'r', encoding='utf-8') as f:
        manifest_data = json.load(f)

    # A nova arquitetura espera o texto bruto diretamente dos metadados da fonte
    texto_bruto = manifest_data.get("metadados_fonte", {}).get("conteudo_sem_formatacao")
    if not texto_bruto:
        logging.error("Campo 'conteudo_sem_formatacao' não encontrado nos metadados do manifesto.")
        raise ValueError("Texto bruto ausente no manifesto.")

    # Monta o payload para a função de parsing
    payload = {
        "id_documento": manifest_data["urn_lexml"],
        "rotulo": manifest_data.get("titulo", manifest_data["urn_lexml"]),
        "fonte": "GOIAS_API", # Assumindo a fonte por enquanto
        "texto_bruto": texto_bruto
    }

    # Executa o pipeline de parsing
    resultado_parsing = parse_document(payload)

    # Aninha os dados do manifesto original na saída para uso do loader
    resultado_parsing['manifesto'] = manifest_data

    # Salva o resultado
    args.outdir.mkdir(parents=True, exist_ok=True)
    urn_slug = manifest_data["urn_lexml"].replace(';', '_')
    output_path = args.outdir / f"{urn_slug}_structured.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultado_parsing, f, ensure_ascii=False, indent=2)

    logging.info(f"Parsing concluído. Saída salva em: {output_path}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main_cli()