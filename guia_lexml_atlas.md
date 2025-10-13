# 📜 Documento de Ontologia LexML-Atlas

**Versão:** 1.1
**Data:** 2025-10-12

## 1. Propósito

Este documento define a **ontologia oficial** e o **dicionário de dados canônico** para o projeto Atlas. Ele serve como a única fonte da verdade para a estrutura, semântica e vocabulários dos dados jurídicos processados e armazenados no sistema.

O padrão é uma adaptação do LexML Brasil, otimizado para uma arquitetura de grafos e os requisitos do MVP.

---

## 2. Modelo Conceitual

A ontologia é centrada em Atos Normativos que contêm Dispositivos, os quais possuem Versões textuais ao longo do tempo.

```
[AtoNormativo] --(CONTEM)--> [Dispositivo] --(POSSUI_VERSAO)--> [VersaoTextual]

[AtoNormativo] --(ALTERA|REVOGA|REGULAMENTA)--> [AtoNormativo]

[Dispositivo] --(REMETE_A)--> [Dispositivo]
```

---

## 3. Entidades Principais (Nós)

### 3.1. AtoNormativo

Representa o ato jurídico integral (Lei, Constituição, etc.).

| Campo | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `urn_lexml` | `string` | URN no padrão LexML. **Obrigatório**. | `br;go;aparecida.goiania;lei.organica;2008-12-16` |
| `tipo_ato` | `string` | Tipo do ato (vocabulário controlado). **Obrigatório**. | `lei organica` |
| `titulo` | `string` | Título completo do ato. | `Lei Orgânica do Município de Aparecida de Goiânia 2008` |
| `ementa` | `string` | Texto que resume o objeto do ato. **Obrigatório**. | `(Texto da ementa)` |
| `entidade_federativa` | `string` | Nível da federação. | `Municipal` |
| `orgao_publicador` | `string` | Órgão responsável pela publicação. | `Câmara Municipal de Aparecida de Goiânia` |
| `data_publicacao` | `date` | Data de publicação na fonte oficial. | `2008-12-16` |
| `fonte_oficial` | `string` | URL ou referência da fonte. **Obrigatório**. | `@fontes/Municipal/...` |
| `hash_fonte` | `string` | SHA-256 do arquivo fonte original. | `(hash)` |
| `situacao_vigencia` | `string` | Status da vigência (vocabulário controlado). **Obrigatório**. | `vigente` |

### 3.2. Dispositivo

Unidade textual dentro de um ato (artigo, parágrafo, etc.).

| Campo | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `rotulo` | `string` | Rótulo do dispositivo. | `Art. 5º` |
| `ordem` | `integer` | Ordem numérica para classificação. | `5` |
| `texto` | `string` | Conteúdo textual do dispositivo. | `"Todos são iguais perante a lei..."` |
| `caminho_estrutural` | `string` | Caminho hierárquico desde o ato. | `art-5/par-1/inc-I` |
| `tipo_dispositivo` | `string` | Tipo da unidade. | `artigo` |

### 3.3. VersaoTextual

Estado de um dispositivo em um período de tempo.

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `vigencia_inicio` | `date` | Início da vigência desta versão. **Obrigatório**. |
| `vigencia_fim` | `date` | Fim da vigência (nulo se vigente). |
| `texto_normalizado` | `string` | Texto limpo e padronizado. |
| `hash_texto` | `string` | SHA-256 do texto normalizado. |
| `origem_alteracao` | `string` | URN do ato que causou esta nova versão. |
| `status_vigencia` | `string` | Status da versão (`vigente`, `revogado`). |

---

## 4. Arestas do Grafo (Relações)

### Relações Estruturais

| Relação | Origem → Destino | Descrição |
| :--- | :--- | :--- |
| `CONTEM` | AtoNormativo → Dispositivo | Relação de pertencimento estrutural. |
| `POSSUI_VERSAO` | Dispositivo → VersaoTextual | Conecta um dispositivo às suas versões. |

### Relações Normativas

| Relação | Origem → Destino | Propriedades | Descrição |
| :--- | :--- | :--- | :--- |
| `ALTERA` | AtoNormativo → AtoNormativo | `escopo`, `pinpoint`, `data_alteracao` | Um ato altera outro (parcial ou totalmente). |
| `REVOGA` | AtoNormativo → AtoNormativo | `escopo`, `pinpoint`, `data_revogacao` | Um ato revoga outro (parcial ou totalmente). |
| `REGULAMENTA` | AtoNormativo → AtoNormativo | `pinpoint`, `referencia_expressa` | Um ato regulamenta outro (geralmente de hierarquia superior). |
| `REMETE_A` | Dispositivo → Dispositivo | `expressao_citada`, `confianca_extracao` | Remissão explícita de um dispositivo a outro. |

---

## 5. Vocabulários Controlados (PT-BR)

### 5.1. `tipo_ato`

- `constituicao`
- `emenda constitucional`
- `lei complementar`
- `lei ordinaria`
- `decreto`
- `decreto legislativo`
- `resolucao`
- `lei organica`

### 5.2. `situacao_vigencia`

- `vigente`
- `revogado_total`
- `revogado_parcial`
- `com_vigencia_diferida`
- `sem_vigencia_definida`

---

## 6. Campos Obrigatórios

- **AtoNormativo:** `urn_lexml`, `tipo_ato`, `ementa`, `fonte_oficial`, `situacao_vigencia`.
- **VersaoTextual:** `vigencia_inicio`.
