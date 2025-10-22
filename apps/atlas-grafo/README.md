# Atlas CEIGEP · Grafo Normativo

Aplicação Next.js hospedável no Vercel que consome as tabelas normalizadas (Supabase) e apresenta um grafo interativo com as relações normativas identificadas pelo pipeline (`dispositivo_relacao`). O objetivo é facilitar a exploração das conexões entre atos (alterações, revogações, citações, etc.).

## Requisitos

- Node.js 20+ (NVM recomendado)
- pnpm `^10` (instalado automaticamente com `corepack enable`)
- Credenciais do Supabase (URL + `SERVICE_ROLE_KEY`)

## Configuração

1. Copie o arquivo `.env.example`:

   ```bash
   cd apps/atlas-grafo
   cp .env.example .env.local
   ```

2. Preencha:

   ```env
   SUPABASE_URL=https://<project>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJI...
   ```

   > **Importante:** use somente o Service Role em rotas de servidor (nunca expose no cliente). No Vercel, cadastre esses valores em *Project Settings → Environment Variables*.

## Desenvolvimento local

```bash
pnpm install           # primeira vez
pnpm dev               # roda em http://localhost:3000
```

O grafo consulta `/api/graph`, que agrega atos e relações em tempo real a partir do Supabase. Ajuste o limite via `?limit=500` na URL se necessário.

## Deploy no Vercel

1. Autentique o CLI (`vercel login`) e vincule o projeto:

   ```bash
    cd apps/atlas-grafo
    vercel link         # selecione o projeto atlas-ceigep
   ```

2. Defina as variáveis (produção e preview):

   ```bash
   vercel env add SUPABASE_URL
   vercel env add SUPABASE_SERVICE_ROLE_KEY
   ```

3. Faça o deploy:

   ```bash
   vercel --prod
   ```

O fluxo também pode ser automatizado via GitHub (build com `pnpm install && pnpm build`).

## Próximas evoluções

- Filtros adicionais: órgão publicador, situação de vigência, período.
- Destaque temporal com timeline para acompanhar versões.
- Suporte a temas/comunidades conforme plano do Graph RAG (`docs/graph_rag.pdf`).
