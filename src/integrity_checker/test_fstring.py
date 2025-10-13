import datetime

duration = 1.2345
urn = "test_urn"
VERSION = "1.0"
json_path = "/path/to/file.json"
overall_pass = True
pg_pass = True
pg_results = {'device_count_match': True, 'hash_set_match': True, 'device_count': 10, 'hash_set': set()}
ground_truth = {'device_count': 10, 'hash_set': set()}


report_content = f"""
# Relatório de Integridade: {urn}

**Data da Verificação:** {datetime.datetime.now(datetime.timezone.utc).isoformat()}
**Versão do Checker:** {VERSION}
**Duração:** {duration:.2f} segundos
**Arquivo Fonte:** {json_path}

## Resumo
* **Status Geral:** {"PASS" if overall_pass else "FAIL"}
"""

print(report_content)
