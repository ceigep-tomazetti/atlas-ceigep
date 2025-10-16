# Guia de Uso dos CLIs do Atlas

Este guia explica, em linguagem simples, como executar as duas ferramentas de linha de comando (CLI) incluídas no projeto Atlas:

- `crawler` – responsável por descobrir atos normativos e salvar os textos brutos.
- `parser` – responsável por transformar os textos brutos em JSON estruturado.

Mesmo quem não tem familiaridade com programação consegue seguir as instruções abaixo.

---

## 1. Preparação do Ambiente

1. **Requisitos básicos**
   - Python 3.10 ou superior instalado.
   - Acesso à internet (as ferramentas consultam a API do Supabase e, opcionalmente, o serviço Gemini).
2. **Instalar dependências**
   ```bash
   cd /Users/tomazetti/Projetos/ceigep-atlas-data
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Configurar variáveis de ambiente**
   - Obrigatórias para o Supabase:
     ```bash
     export SUPABASE_URL="https://<seu-projeto>.supabase.co"
     export SUPABASE_SERVICE_ROLE_KEY="<chave-service-role>"
     ```
   - Opcionais para uso do LLM (Gemini):
     ```bash
     export GEMINI_API_KEY="<chave-gemini>"
     # Opcional: definir um modelo específico
     export GEMINI_MODEL="gemini-1.5-pro"
     ```

Se essas variáveis não estiverem configuradas, os CLIs exibem mensagens de erro informando o que falta.

---

## 2. Convenções Gerais

- Todos os comandos devem ser executados a partir da pasta raiz do projeto `/Users/tomazetti/Projetos/ceigep-atlas-data`.
- Use `python -m` para executar os módulos:
  - Crawler: `python -m src.crawler.main`
  - Parser: `python -m src.parser.main`
- Inclua `--help` em qualquer comando para ver um resumo rápido das opções.

---

## 3. CLI do Crawler (`src/crawler/main.py`)

### 3.1. O que ele faz

1. **Descoberta** – consulta as fontes cadastradas no Supabase e registra novos atos com metadados.
2. **Extração** – baixa o texto bruto (sem formatação) e envia para o Supabase Storage.
3. **Histórico** – registra cada execução com contagem de itens novos, duplicados e falhas.

Por padrão, o crawler realiza descoberta e, na sequência, extração.

### 3.2. Parâmetros disponíveis

| Opção | Explicação |
| ----- | ---------- |
| `--origin-id UUID` | Processa apenas a origem com o UUID informado. Pode repetir a flag para múltiplas origens. |
| `--since AAAA-MM-DD` | Data inicial do período a consultar (legislação). |
| `--until AAAA-MM-DD` | Data final do período a consultar (legislação). |
| `--limit N` | Limita a quantidade de atos por origem. Útil para testes. |
| `--dry-run` | Faz tudo, exceto gravar dados no banco/Storage. Apenas exibe logs. |
| `--backfill` | Executa descoberta mês a mês para trás (loop infinito até CTRL+C). |
| `--extract` | Pule a descoberta e execute somente a extração de textos pendentes. |
| `--discover-only` | Executa somente descoberta; não chama a extração ao final. |

### 3.3. Exemplos práticos

1. **Executar fluxo completo do mês atual (descoberta + extração)**  
   ```bash
   python -m src.crawler.main
   ```

2. **Processar um período específico para a origem de Goiás (exemplo de UUID real)**  
   ```bash
   python -m src.crawler.main \
      --origin-id fd64e393-159f-4484-9ea4-e9437753791d \
      --since 2025-01-01 --until 2025-01-31
   ```

3. **Testar sem gravar nada (dry-run) e limitar a 5 itens**  
   ```bash
   python -m src.crawler.main --dry-run --limit 5
   ```

4. **Executar apenas a extração para itens já descobertos**  
   ```bash
   python -m src.crawler.main --extract --limit 10
   ```

5. **Rodar backfill contínuo (aperta CTRL+C para parar)**  
   ```bash
   python -m src.crawler.main --backfill --limit 50
   ```

### 3.4. O que esperar nos resultados

- Novos registros aparecem na tabela `fonte_documento` com status `descoberto`.
- Após extração, o status muda para `processado` e os textos brutos ficam no bucket `textos_brutos/`.
- Cada execução é registrada na tabela `fonte_origem_execucao`.
- Em caso de erro, o log exibirá a URN que falhou; tente reprocessar após corrigir o problema.

---

## 4. CLI do Parser (`src/parser/main.py`)

### 4.1. O que ele faz

1. Baixa o texto bruto do Supabase Storage, usando o caminho salvo em `fonte_documento`.
2. Gera JSON estruturado com a hierarquia de dispositivos (Artigos, §§, incisos, etc.).
3. Opcionalmente consulta o Gemini para comparar resultados e registrar sugestões.
4. Salva o JSON em `textos_estruturados/` e atualiza o status `status_parsing`.

### 4.2. Parâmetros disponíveis

| Opção | Explicação |
| ----- | ---------- |
| `--origin-id UUID` | Restringe a origem processada. Pode repetir para várias. |
| `--limit N` | Processa somente N atos por origem. |
| `--dry-run` | Não salva nada; imprime resumos no terminal para inspeção manual. |
| `--mode {deterministic,llm,both,review}` | Define o modo de operação (veja abaixo). |
| `--llm-model NOME` | Escolhe o modelo Gemini (se `GEMINI_API_KEY` estiver configurada). |
| `--review-sample-ratio 0-1` | No modo `review`, percentual de itens verificados pelo LLM. |
| `--review-sample-seed NUM` | Seed opcional para tornar a amostragem reprodutível. |

**Modos de operação**

- `deterministic` (padrão): usa apenas as heurísticas internas (sem LLM).
- `llm`: ignora o determinístico e salva somente a saída do Gemini.
- `both`: executa ambos e salva a versão determinística; usa o LLM apenas para comparação.
- `review`: executa o determinístico sempre; compara com o LLM em uma amostra e marca divergências para revisão manual (registrando sugestões).

### 4.3. Exemplos práticos

1. **Processar todos os itens pendentes usando apenas o parser determinístico**  
   ```bash
   python -m src.parser.main
   ```

2. **Limitar a origem de Goiás e processar somente 10 itens**  
   ```bash
   python -m src.parser.main \
      --origin-id fd64e393-159f-4484-9ea4-e9437753791d \
      --limit 10
   ```

3. **Executar em modo “review” com amostragem de 20% (necessita GEMINI_API_KEY)**  
   ```bash
   python -m src.parser.main \
      --mode review \
      --review-sample-ratio 0.2 \
      --review-sample-seed 42
   ```

4. **Rodar em dry-run para inspecionar a saída sem salvar nada**  
   ```bash
   python -m src.parser.main --dry-run --limit 3
   ```
   O comando imprime o texto normalizado e a lista de dispositivos detectados.

5. **Gerar JSON usando exclusivamente o LLM (experimental)**  
   ```bash
   python -m src.parser.main --mode llm --limit 2
   ```
   Útil para comparar com o resultado heurístico em ambiente de testes.

### 4.4. O que esperar nos resultados

- Sucesso: os registros ganham `status_parsing = processado`, hash e caminho do JSON.
- Divergência no modo `review`: o ato recebe `status_parsing = falha` e uma sugestão é registrada na tabela `llm_parser_sugestao`.
- Falha ao baixar texto ou ao gerar JSON: o status também passa para `falha`. Basta corrigir a causa e reexecutar.

---

## 5. Dúvidas e Problemas Comuns

- **“Supabase URL/Key não configurados”** – verifique as variáveis de ambiente `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`.
- **“LLM não configurado”** – o aviso aparece quando `GEMINI_API_KEY` não está definido. Os modos `deterministic` e `dry-run` funcionam sem o LLM.
- **Teste seguro** – use sempre `--dry-run` antes de execuções grandes em produção.
- **Interromper execuções longas** – pressione `CTRL+C`. O processo atual será interrompido com segurança; basta reiniciar quando desejar.

Se ainda restarem dúvidas, consulte o diário de bordo (`docs/diario_de_bordo.md`) para entender o histórico das decisões ou abra uma issue descrevendo o problema.

---

Com estas instruções, qualquer pessoa consegue operar o pipeline básico do Atlas sem precisar conhecer os detalhes técnicos do código.
