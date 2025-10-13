# -*- coding: utf-8 -*-

"""
gerador_urn.py

Script para a geração de URNs LexML padronizadas para atos normativos
do município de Aparecida de Goiânia.
"""

import datetime
from typing import Union

# Vocabulário controlado para tipo_ato
VOCABULARIO_TIPO_ATO = {
    'constituicao', 'emenda.constitucional', 'lei.complementar',
    'lei', 'decreto', 'decreto.legislativo', 'resolucao', 'lei.organica'
}

def gerar_urn_municipal(
    tipo_ato: str,
    data_publicacao: datetime.date,
    numero_ato: Union[int, str, None],
    uf: str = "go",
    municipio: str = "aparecida.goiania"
) -> str:
    """
    Gera uma URN LexML padronizada para um ato normativo municipal.

    A URN será composta por 6 partes obrigatórias:
    `br;{uf};{municipio};{tipo_ato};{data_publicacao};{numero_do_ato}`

    Args:
        tipo_ato (str): O tipo do ato (ex: 'lei.organica', 'lei.complementar', 'lei').
                        Deve pertencer ao VOCABULARIO_TIPO_ATO.
        data_publicacao (datetime.date): A data de publicação do ato.
        numero_ato (Union[int, str, None]): O número oficial do ato.
                                            Pode ser None para Lei Orgânica.
        uf (str): Sigla da Unidade Federativa (padrão: "go").
        municipio (str): Nome do município normalizado (padrão: "aparecida.goiania").

    Returns:
        str: A URN LexML formatada.

    Raises:
        ValueError: Se o tipo_ato for inválido ou o numero_ato for obrigatório e não fornecido/inválido.
        TypeError: Se data_publicacao não for um objeto datetime.date.

    Exemplos (doctest):
    >>> from datetime import date
    >>> gerar_urn_municipal('lei.complementar', date(2015, 3, 30), 123)
    'br;go;aparecida.goiania;lei.complementar;2015-03-30;123'
    >>> gerar_urn_municipal('lei', date(2020, 6, 15), '04567')
    'br;go;aparecida.goiania;lei;2020-06-15;4567'
    >>> gerar_urn_municipal('lei.organica', date(2008, 12, 16), None)
    'br;go;aparecida.goiania;lei.organica;2008-12-16;2008'
    >>> gerar_urn_municipal('decreto', date(2021, 1, 1), 89)
    'br;go;aparecida.goiania;decreto;2021-01-01;89'
    >>> gerar_urn_municipal('lei', date(2020, 1, 1), 'abc')
    Traceback (most recent call last):
        ... 
    ValueError: numero_ato inválido para tipo_ato=lei. Deve ser numérico.
    >>> gerar_urn_municipal('lei', date(2020, 1, 1), None)
    Traceback (most recent call last):
        ... 
    ValueError: numero_ato é obrigatório para tipo_ato=lei.
    >>> gerar_urn_municipal('tipo.invalido', date(2020, 1, 1), 1)
    Traceback (most recent call last):
        ... 
    ValueError: tipo_ato inválido: tipo.invalido. Vocabulário permitido: {'constituicao', 'emenda.constitucional', 'lei.complementar', 'lei', 'decreto', 'decreto.legislativo', 'resolucao', 'lei.organica'}
    """
    if not isinstance(tipo_ato, str) or not tipo_ato:
        raise ValueError("O tipo_ato deve ser uma string não vazia.")
    if not isinstance(data_publicacao, datetime.date):
        raise TypeError("data_publicacao deve ser um objeto datetime.date.")

    # Normalização de tipo_ato e validação contra vocabulário
    tipo_ato_norm = tipo_ato.lower().replace(" ", ".")
    if tipo_ato_norm not in VOCABULARIO_TIPO_ATO:
        raise ValueError(
            f"tipo_ato inválido: {tipo_ato_norm}. Vocabulário permitido: {VOCABULARIO_TIPO_ATO}"
        )

    data_norm = data_publicacao.strftime('%Y-%m-%d')
    
    numero_norm = None
    if tipo_ato_norm == 'lei.organica':
        if numero_ato is None or str(numero_ato).strip() == '':
            numero_norm = str(data_publicacao.year)
        else:
            # Ainda valida se fornecido, mas permite None
            if not str(numero_ato).isdigit():
                raise ValueError(f"numero_ato inválido para tipo_ato={tipo_ato_norm}. Deve ser numérico ou None.")
            numero_norm = str(int(numero_ato)) # Remove zeros à esquerda
    else:
        if numero_ato is None or str(numero_ato).strip() == '':
            raise ValueError(f"numero_ato é obrigatório para tipo_ato={tipo_ato_norm}.")
        if not str(numero_ato).isdigit():
            raise ValueError(f"numero_ato inválido para tipo_ato={tipo_ato_norm}. Deve ser numérico.")
        numero_norm = str(int(numero_ato)) # Remove zeros à esquerda

    urn = f"br;{uf.lower()};{municipio.lower().replace(' ', '.')};{tipo_ato_norm};{data_norm};{numero_norm}"
    return urn

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)

    print("\n--- Testes Adicionais ---")

    # Happy paths
    print("\nHappy Path: Lei Complementar")
    data_lc_123 = datetime.date(2015, 3, 30)
    urn_lc_123 = gerar_urn_municipal('lei.complementar', data_lc_123, 123)
    print(f"URN Gerada: {urn_lc_123}")
    assert urn_lc_123 == "br;go;aparecida.goiania;lei.complementar;2015-03-30;123"

    print("\nHappy Path: Lei Ordinária com string numérica")
    data_lei_4567 = datetime.date(2020, 6, 15)
    urn_lei_4567 = gerar_urn_municipal('lei', data_lei_4567, "04567")
    print(f"URN Gerada: {urn_lei_4567}")
    assert urn_lei_4567 == "br;go;aparecida.goiania;lei;2020-06-15;4567"

    print("\nHappy Path: Lei Orgânica com numero_ato=None")
    data_lo = datetime.date(2008, 12, 16)
    urn_lo = gerar_urn_municipal('lei.organica', data_lo, None)
    print(f"URN Gerada: {urn_lo}")
    assert urn_lo == "br;go;aparecida.goiania;lei.organica;2008-12-16;2008"
    
    print("\nHappy Path: Lei Orgânica com numero_ato fornecido")
    data_lo_num = datetime.date(2008, 12, 16)
    urn_lo_num = gerar_urn_municipal('lei.organica', data_lo_num, '2008')
    print(f"URN Gerada: {urn_lo_num}")
    assert urn_lo_num == "br;go;aparecida.goiania;lei.organica;2008-12-16;2008"


    # Testes de Erro
    print("\nTeste de Erro: tipo_ato inválido")
    try:
        gerar_urn_municipal('tipo.desconhecido', datetime.date(2020, 1, 1), 1)
    except ValueError as e:
        print(f"Erro esperado: {e}")
        assert "tipo_ato inválido" in str(e)

    print("\nTeste de Erro: data_publicacao tipo incorreto")
    try:
        gerar_urn_municipal('decreto', '2021-01-01', 89)
    except TypeError as e:
        print(f"Erro esperado: {e}")
        assert "datetime.date" in str(e)

    print("\nTeste de Erro: numero_ato não numérico para lei")
    try:
        gerar_urn_municipal('lei', datetime.date(2020, 1, 1), 'abc')
    except ValueError as e:
        print(f"Erro esperado: {e}")
        assert "Deve ser numérico" in str(e)

    print("\nTeste de Erro: numero_ato None para lei")
    try:
        gerar_urn_municipal('lei', datetime.date(2020, 1, 1), None)
    except ValueError as e:
        print(f"Erro esperado: {e}")
        assert "obrigatório" in str(e)

    print("\nTeste de Erro: numero_ato vazio para lei")
    try:
        gerar_urn_municipal('lei', datetime.date(2020, 1, 1), '')
    except ValueError as e:
        print(f"Erro esperado: {e}")
        assert "obrigatório" in str(e)

    print("\nTodos os testes concluídos.")