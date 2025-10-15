# src/crawler/spiders/goias_api.py
import requests
import json
import logging
import re
import calendar
from datetime import datetime
from urllib.parse import urlencode

BASE_URL = "https://legisla.casacivil.go.gov.br/api/v2/pesquisa/legislacoes/dados_abertos.json"
USER_AGENT = "Mozilla/5.0 (compatible; AtlasProjectCrawler/1.0; +https://github.com/tomazetti/ceigep-atlas-data)"

import unicodedata

def slugify(text):
    """
    Converte um texto como 'Portaria Orçamentária' para 'portaria.orcamentaria'.
    Remove acentos e caracteres especiais.
    """
    if not text:
        return "desconhecido"
    # Normaliza para decompor acentos
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    # Remove caracteres não permitidos
    text = re.sub(r'[^a-z0-9\s/.-]', '', text)
    # Substitui espaços e barras por ponto
    text = re.sub(r'[\s/]+', '.', text)
    return text

def collect():
    """
    Coleta toda a legislação de Goiás, iterando mês a mês e usando 'yield'
    para retornar cada fonte individualmente.
    """
    logging.info("Iniciando coleta completa da legislação de Goiás.")
    current_year = datetime.now().year

    for year in range(current_year, 1989, -1): # Itera de {current_year} até 1990
        year_results = 0
        for month in range(1, 13):
            # Define o primeiro e o último dia do mês
            start_date = f"{year}-{month:02d}-01"
            last_day = calendar.monthrange(year, month)[1]
            end_date = f"{year}-{month:02d}-{last_day:02d}"

            params = {
                'numero': '', 'conteudo': '', 'tipo_legislacao': '', 'estado_legislacao': '',
                'categoria_legislacao': '', 'ementa': '', 'autor': '', 'ano': '',
                'periodo_inicial_legislacao': start_date,
                'periodo_final_legislacao': end_date,
                'periodo_inicial_diario': '', 'periodo_final_diario': '',
                'termo': '', 'semantico': ''
            }
            
            try:
                response = requests.get(BASE_URL, params=params, headers={'User-Agent': USER_AGENT}, timeout=90)
                response.raise_for_status()
                data = response.json()

                if len(data) >= 1000:
                    logging.warning(f"Atingido o limite de 1000 resultados para {year}-{month:02d}. Alguns dados podem ter sido perdidos.")

                for item_str in data:
                    try:
                        item = json.loads(item_str)
                        
                        if not item.get('diarios') or not item['diarios'][0].get('link_download'):
                            continue

                        tipo_slug = slugify(item.get('tipo_legislacao'))
                        date_obj = datetime.strptime(item['data_legislacao'], '%d/%m/%Y')
                        formatted_date = date_obj.strftime('%Y-%m-%d')
                        numero = item.get('numero', '').replace('.', '')

                        urn = f"br;go;estadual;{tipo_slug};{formatted_date};{numero}"
                        url_fonte = item['diarios'][0]['link_download']

                        yield {
                            "urn": urn,
                            "url_fonte": url_fonte,
                            "metadados": item
                        }
                        year_results += 1

                    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
                        logging.warning(f"Item da API de Goiás inválido ignorado: {e} - Item: {item_str[:200]}")

            except requests.RequestException as e:
                logging.error(f"Erro ao buscar dados para o período {start_date} a {end_date}: {e}")
        
        if year_results > 0:
            logging.info(f"Coletadas {year_results} fontes para o ano de {year}.")