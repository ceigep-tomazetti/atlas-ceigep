# 🏛️ Esquema de URN LexML para Atos Municipais

**Versão:** 1.0
**Data:** 2025-10-12

## 1. Objetivo

Este documento define o padrão de construção de Identificadores Uniformes de Recurso (URN) para os atos normativos do município de Aparecida de Goiânia, seguindo as boas práticas do padrão LexML Brasil.

## 2. Estrutura Padrão

A URN será composta por 6 partes obrigatórias, separadas por ponto e vírgula (`;`).

`br;go;aparecida.goiania;{tipo_ato};{data_publicacao};{numero_do_ato}`

### Detalhamento dos Componentes:

1.  **País:** `br` (Fixo para Brasil)
2.  **Estado:** `go` (Fixo para Goiás)
3.  **Município:** `aparecida.goiania` (Nome do município em formato normalizado)
4.  **Tipo do Ato:** O tipo do ato normativo em formato normalizado e singular. Exemplos: `lei.organica`, `lei.complementar`, `lei`, `decreto`.
5.  **Data de Publicação:** A data em que o ato foi publicado, no formato `AAAA-MM-DD`.
6.  **Número do Ato:** O número oficial do ato, sem pontos ou separadores. Para a Lei Orgânica, que não possui número, usaremos o ano de sua promulgação.

## 3. Exemplos Práticos

-   **Lei Orgânica de 2008:**
    -   `br;go;aparecida.goiania;lei.organica;2008-12-16;2008`

-   **Lei Complementar nº 123 de 30 de março de 2015:**
    -   `br;go;aparecida.goiania;lei.complementar;2015-03-30;123`

-   **Lei Ordinária nº 4.567 de 15 de junho de 2020:**
    -   `br;go;aparecida.goiania;lei;2020-06-15;4567`

-   **Decreto nº 89 de 1 de janeiro de 2021:**
    -   `br;go;aparecida.goiania;decreto;2021-01-01;89`

Este padrão garante que cada ato normativo do município tenha um identificador único e significativo, facilitando a automação e a interoperabilidade.
