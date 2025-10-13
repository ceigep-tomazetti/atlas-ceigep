# ✅ Validação do Parser vs. LexML (Tarefa 3.3)

**Escopo:** CF/1988, CE-GO/1989, LO Aparecida/2008
**Método:** Validação manual/documental (URN conforme LexML Parte 2) + verificação estrutural e de auditoria nos JSONs do projeto.
**Nota:** Tentativas de uso do **SRU LexML** não retornaram resultados; validação automática de metadados ficou inviável neste momento. Aguardará re-tentativa futura.

---

## 1) Regras usadas nesta validação

**URN (resumo prático):**

* Federal/Estadual (5 partes): `br;{esfera};{tipo_ato};{AAAA-MM-DD}`
  Ex.: `br;federal;constituicao;1988-10-05`
* Municipal (6 partes): `br;go;aparecida.goiania;{tipo_ato};{AAAA-MM-DD};{numero}`
  Para **Lei Orgânica**, usar **ano** como número: `…;lei.organica;2008-12-16;2008`

**Hierarquia esperada:**

* Artigo → (Parágrafo(s) §) → Inciso(s) → Alínea(s) → Item(ns)
* **Caput** fica no **nó do artigo** (ou do dispositivo pai), antes do primeiro filho.
* Caminho estrutural: `art-5/par-1/inc-3/ali-b/item-2` (ordem iniciando em 1 por nível).

**Auditoria mínima:**

* `source_url`, `retrieved_at`, `content_length`, `sha256_origem`, `user_agent`, `parser_versao`, `gerado_em`.
* `hash_texto` por dispositivo (mesmo quando `texto_normalizado` é `""`).

---

## 2) Checklist — Constituição Federal (CF/1988)

**Identificação e Metadados**

* [x] URN: `br;federal;constituicao;1988-10-05` (formato e data)
* [x] Tipo de ato: “constituição” (vocabulário PT-BR)
* [x] Data de publicação: `1988-10-05`
* [x] Órgão publicador: “Presidência da República” (coerente com a fonte)
* [x] Título/ementa coerentes com a fonte usada

**Estrutura (JSON canônico)**

* [x] Art. 1º: caput separado; sem filhos indevidos
* [x] Art. 2º–4º: estrutura simples correta
* [x] **Art. 5º**:

  * [x] Caput no nó do artigo
  * [x] Incisos I… (ordem crescente; rótulo literal preservado)
  * [x] Parágrafos (§) quando existentes (filhos diretos do artigo)
  * [x] Alíneas/Itens corretamente aninhados onde houver
  * [x] Caminhos estruturais válidos (amostragem: `art-5/inc-1`, `art-5/inc-12/ali-b`)

**Auditoria e Hashes**

* [x] `sha256_origem` bate com o metadado do arquivo bruto
* [x] `hash_texto` distinto por dispositivo com conteúdo
* [x] Campos de auditoria completos

> Observações CF: A validação manual confirma que a estrutura hierárquica do Art. 5º, incluindo incisos e alíneas, foi capturada corretamente. Pequenos artefatos textuais como "(Vide Lei...)" ainda estão presentes e podem ser removidos em uma fase de normalização mais fina.

---

## 3) Checklist — Constituição do Estado de Goiás (CE-GO/1989)

**Identificação e Metadados**

* [x] URN: `br;go;constituicao;1989-10-05`
* [x] Tipo de ato: “constituição”
* [x] Data: `1989-10-05`
* [x] Órgão publicador: “Governo do Estado de Goiás – Casa Civil”

**Estrutura (JSON recursivo em PDF, Art. 1º–5º)**

* [x] Art. 1º–5º presentes
* [x] Caput em cada artigo
* [x] Parágrafos quando existirem; incisos/alíneas/itens aninhados corretamente
* [x] Caminhos e ordens corretos em amostragem (ex.: `art-1/par-2/inc-1`)

**Auditoria e Hashes**

* [x] `sha256_origem` conforme metadados
* [x] `hash_texto` por nó
* [x] Auditoria completa

> Observações CE-GO: O parser recursivo de PDF funcionou bem, identificando corretamente a hierarquia de parágrafos, incisos e alíneas nos primeiros artigos.

---

## 4) Checklist — Lei Orgânica de Aparecida (2008)

**Identificação e Metadados**

* [x] URN: `br;go;aparecida.goiania;lei.organica;2008-12-16;2008`
* [x] Tipo de ato: “lei orgânica”
* [x] Data: `2008-12-16`
* [x] Órgão publicador: “Câmara Municipal de Aparecida de Goiânia”

**Estrutura (JSON recursivo em PDF, Art. 1º–5º)**

* [x] Art. 1º–5º com caput
* [x] Parágrafos/Incisos/Alíneas/Itens aninhados corretamente
* [x] Caminhos e ordens corretos (amostragem)

**Auditoria e Hashes**

* [x] `sha256_origem` conforme metadados
* [x] `hash_texto` por nó
* [x] Auditoria completa

> Observações LO: Similar à CE-GO, o parser de PDF lidou bem com a estrutura, validando a abordagem para textos extraídos de PDF.

---

## 5) Resultado final

* **SRU/Validação automática:** indisponível no momento (endpoint sem resposta útil).
* **Validação manual/documental:** **APROVADA** nos 3 atos avaliados (CF/1988, CE-GO/1989, LO/2008), conforme checks acima.
* **Recomendação:** manter a seção “SRU” em aberto para re-teste futuro; por ora, a validação baseada em documento e estrutura interna é suficiente para o MVP.
