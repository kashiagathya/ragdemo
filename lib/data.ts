import type { KnowledgeDocument, RetrievedDocument } from "@/types";

const seed = [
  [
    "RAG Primer.md",
    "Retrieval-Augmented Generation, or RAG, combines a language model with a retrieval system. The retriever finds relevant knowledge before generation, so an answer can be grounded in external documents.",
  ],
  [
    "Embeddings Guide.txt",
    "Embeddings are dense numerical representations of meaning. Similar ideas land near one another in vector space, making semantic search possible even when a question and document use different words.",
  ],
  [
    "Vector Stores.md",
    "A vector database stores embeddings with metadata and returns nearest neighbors by similarity. Pinecone is a managed vector database commonly used to serve low-latency retrieval in production.",
  ],
  [
    "Agents Handbook.md",
    "An AI agent is an orchestrator that can inspect a question, select a tool, and combine tool results with a language model. Good agents avoid unnecessary retrieval when a calculation is enough.",
  ],
  [
    "Prompt Engineering.md",
    "A strong prompt gives the model a task, constraints, and useful context. In a RAG prompt, retrieved passages are clearly separated from the user question and system instructions.",
  ],
];
export const documents: KnowledgeDocument[] = seed.map(
  ([name, text], index) => ({
    id: `doc-${index + 1}`,
    name,
    type: name.endsWith(".md") ? "Markdown" : "Text",
    text,
    chunks: [text],
    status: "Indexed",
    createdAt: "2026-09-03",
  }),
);
export function searchDocuments(query: string, topK = 5): RetrievedDocument[] {
  const terms = query.toLowerCase().split(/\\W+/).filter(Boolean);
  return documents
    .map((doc, index) => {
      const matches = terms.filter((term) =>
        doc.text.toLowerCase().includes(term),
      ).length;
      const score = Math.min(
        0.98,
        0.48 + matches * 0.09 + (documents.length - index) * 0.012,
      );
      return {
        id: doc.id,
        source: doc.name,
        chunk: 1,
        score: Number(score.toFixed(3)),
        text: doc.text,
        metadata: { type: doc.type, documentId: doc.id },
        x: 18 + ((index * 23) % 66),
        y: 22 + ((index * 37) % 60),
      };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, topK);
}
