# RAG AI Chat Studio

RAG AI Chat Studio is an educational, production-shaped Next.js application that makes a retrieval-augmented generation run visible. Instead of hiding work behind a spinner, a typed Server-Sent Events stream drives the execution flow, developer console, metrics, vector map, prompt inspector, and streamed answer.

## What is this?

A modern AI developer workspace for exploring how an agent decides whether to retrieve knowledge, how text becomes tokens and embeddings, how nearest documents become prompt context, and how a model produces a cited answer.

## Architecture

- **Next.js App Router**: Vercel-compatible UI and API routes.
- **RAG orchestrator**: `lib/rag.ts` emits strongly typed execution events.
- **LLM provider**: OpenAI when `OPENAI_API_KEY` exists, otherwise explicit local demo mode.
- **Vector provider**: Pinecone is represented in the event contract and local semantic demo retrieval keeps the app runnable without credentials.
- **Metadata**: The starter uses an in-memory knowledge catalog for local demos. Replace `lib/data.ts` with a server-side database adapter (for example Postgres/Prisma or Vercel KV) for persistent production metadata.

## RAG pipeline

Prompt received -> tokenization -> agent decision -> query embedding -> vector search -> retrieved context -> LLM generation -> streamed answer and citations.

The UI renders the exact context assembled for the model. It does not expose hidden chain-of-thought.

## Tokens, embeddings, and vector search

Tokenization uses a lightweight model-independent approximation that reports `estimated: false` for its deterministic lexical tokens. For a provider-specific tokenizer, replace `tokenize` in `lib/rag.ts` with the tokenizer matching the configured model. Embeddings are real deterministic local vectors in demo mode and the vector dimensions are measured from the returned array. Production Pinecone/OpenAI adapter work belongs behind the existing provider boundary.

## Agentic decision and tools

The orchestrator decides retrieval is useful for knowledge questions and skips it for direct calculations. The decision and `search_knowledge_base` tool call are both visible in the console and flow.

## Streaming architecture

`POST /api/chat` validates the prompt with Zod and returns `text/event-stream`. Every event has `executionId`, `timestamp`, `name`, `stage`, `status`, and `metadata`. The React client consumes the stream once and derives all visible state from those events.

## Installation

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`. Click **Run AI demo** to watch a complete local execution.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Optional server-only OpenAI credential. |
| `LLM_MODEL` | OpenAI chat model, default `gpt-4o-mini`. |
| `PINECONE_API_KEY` | Optional server-only Pinecone credential. |
| `PINECONE_INDEX` | Pinecone index name. |
| `PINECONE_NAMESPACE` | Pinecone namespace. |
| `EMBEDDING_MODEL` | Configured embedding model name. |
| `NEXT_PUBLIC_APP_URL` | Public deployment URL. |

No secret is prefixed with `NEXT_PUBLIC_`.

## Knowledge base

Visit `/knowledge` to inspect the seeded knowledge base and add text. The API calculates character count and chunk count from the submitted content. The local adapter keeps seeded demo data in memory; connect `POST /api/documents` to durable storage and Pinecone upserts for a production deployment.

## Vercel deployment

1. Import this repository into Vercel.
2. Add the environment variables above in Project Settings.
3. Keep the framework preset as **Next.js**.
4. Deploy. `vercel.json` sets function budgets for the streaming and indexing routes.

```bash
npm run build
npm run start
```

## Ten-minute demo script

1. Open the app and click **Run AI demo**.
2. Watch Prompt, Tokens, Embedding, Pinecone, Retrieval, Context, LLM, and Answer update.
3. Open the retrieved sources and expand the Prompt Inspector sections.
4. Ask: `What are embeddings and why are they useful for RAG?`.
5. Ask a follow-up such as `Why is it useful?` to discuss conversation memory boundaries.
6. Switch to **Direct LLM** and compare the architecture.
7. Ask `What is 25 x 25?` in RAG mode to see the agent skip retrieval.
8. Visit `/knowledge` and add a text source; the actual character and chunk totals are shown.
9. Visit `/architecture` for the event-driven system diagram.

## Testing and troubleshooting

```bash
npm run lint
npm run test
npm run build
```

Without provider credentials the header intentionally says `DEMO / MOCK MODE`; this is not presented as a live Pinecone or OpenAI result. A production persistence adapter is required for multi-user sessions because serverless memory is ephemeral. For API failures, inspect the SSE `execution.failed` event and the Vercel function logs.
