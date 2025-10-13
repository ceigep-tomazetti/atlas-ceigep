# 🏛️ Política de Controle de Versões e Vigência

**Versão:** 1.1
**Data:** 2025-10-12

## 1. Objetivo

Este documento define a política para o controle de versionamento temporal e o status de vigência dos textos legais no sistema Atlas. O objetivo é garantir uma trilha de auditoria completa e a capacidade de reconstruir o estado da legislação em qualquer ponto no tempo.

## 2. Padrão de Dados Temporais

- **Datas e Fusos:** Todas as datas (`DATE`) e timestamps (`TIMESTAMPTZ`) devem ser armazenadas no padrão **ISO-8601** e normalizadas para o fuso horário **UTC**.
- **Entidade Central:** A rastreabilidade temporal é implementada através da entidade `VersaoTextual`.
- **Imutabilidade:** Uma `VersaoTextual` existente **nunca é alterada ou apagada**. Modificações legislativas sempre geram uma nova `VersaoTextual`.

## 3. Controle de Vigência

### 3.1. Campos de Controle

A vigência é controlada por dois campos na `VersaoTextual`:

-   `vigencia_inicio` (DATE, Obrigatório): Data em que a versão passou a valer.
-   `vigencia_fim` (DATE, Opcional): Data em que a versão deixou de valer. `NULL` indica que a versão continua vigente.

### 3.2. Vacatio Legis e Vigência Diferida

Se a data de entrada em vigor de uma lei for diferente da data de publicação, o campo `vigencia_inicio` da primeira `VersaoTextual` de seus dispositivos deve refletir a **data de entrada em vigor**, não a data de publicação do ato.

### 3.3. Suspensão de Eficácia

- **Novo Status:** Para lidar com suspensão de eficácia (ex: por decisão judicial), o vocabulário do campo `status_vigencia` incluirá o valor `suspensa`.
- **Procedimento:** Uma nova `VersaoTextual` não é criada. Em vez disso, a versão atualmente vigente tem seu status alterado para `suspensa`. Uma propriedade adicional, como `evento_suspensao`, deve ser adicionada para registrar a URN do ato ou o número do processo judicial que causou a suspensão.

## 4. Regras de Integridade (Validação no ETL)

O processo de ETL é responsável por garantir as seguintes regras antes de carregar os dados:

1.  **Unicidade de Versão Ativa:** O ETL deve validar que, para um mesmo `Dispositivo`, no máximo uma `VersaoTextual` pode ter `vigencia_fim` como `NULL`.
2.  **Não-sobreposição de Intervalos:** O ETL deve garantir que os intervalos de `[vigencia_inicio, vigencia_fim]` de todas as `VersaoTextual` de um mesmo `Dispositivo` não se sobreponham.

## 5. Auditoria e Rastreamento

-   `AtoNormativo.hash_fonte`: Garante a integridade do documento original coletado.
-   `VersaoTextual.hash_texto`: Garante a integridade do texto normalizado de uma versão.
-   `VersaoTextual.origem_alteracao_urn`: Preenchido com a URN do ato que gerou uma nova versão, permitindo rastrear a causalidade das mudanças.

## 6. Procedimento de Retificação (Errata)

Correções em textos já publicados (erratas) não alteram registros existentes. O procedimento correto é:

1.  Ingerir a errata como um novo `AtoNormativo` (ex: `tipo_ato: 'errata'`).
2.  Este ato de errata deve ter uma relação (ex: `:RETIFICA`) com o `AtoNormativo` original.
3.  A errata dispara a criação de uma **nova `VersaoTextual`** para o dispositivo corrigido, com o texto ajustado.
4.  A `vigencia_inicio` da nova versão é a data de publicação da errata. A `vigencia_fim` da versão anterior é preenchida com essa mesma data.