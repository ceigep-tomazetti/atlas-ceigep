-- Migração 001: Seed da origem API Casa Civil Goiás

BEGIN;

INSERT INTO public.fonte_origem (
    nome,
    esfera,
    orgao_responsavel,
    url_base,
    formato_padrao,
    autenticacao_requerida,
    descricao,
    parametros_api,
    frequencia_atualizacao,
    status,
    observacoes
) VALUES (
    'API Casa Civil Goiás',
    'estadual',
    'Secretaria da Casa Civil do Estado de Goiás',
    'https://legisla.casacivil.go.gov.br/api/v2/pesquisa/legislacoes/dados_abertos.json',
    'json',
    false,
    'Endpoint de dados abertos que retorna legislações estaduais com filtros por período, tipo e autor.',
    '{
        "limite_resposta": 1000,
        "parametros_padrao": {
            "periodo_inicial_legislacao": "YYYY-MM-01",
            "periodo_final_legislacao": "YYYY-MM-DD",
            "numero": "",
            "conteudo": "",
            "tipo_legislacao": "",
            "estado_legislacao": "",
            "categoria_legislacao": "",
            "ementa": "",
            "autor": "",
            "ano": "",
            "periodo_inicial_diario": "",
            "periodo_final_diario": "",
            "termo": "",
            "semantico": ""
        }
    }'::jsonb,
    'diária',
    'ativo',
    'Limite de 1000 itens por requisição; ideal realizar coletas mensais com paginação manual.'
) ON CONFLICT (nome) DO NOTHING;

COMMIT;
