export type Stage = "prompt" | "tokens" | "embedding" | "agent" | "search" | "retrieval" | "context" | "llm" | "answer";
export type EventName = "execution.started" | "prompt.received" | "tokenization.started" | "tokenization.completed" | "embedding.started" | "embedding.completed" | "agent.started" | "agent.decision" | "tool.started" | "tool.completed" | "vector.search.started" | "vector.search.completed" | "context.started" | "context.completed" | "llm.started" | "llm.token" | "llm.completed" | "execution.completed" | "execution.failed";
export type EventStatus = "waiting" | "running" | "completed" | "failed";
export type AIEvent = { executionId:string; timestamp:string; name:EventName; stage:Stage; status:EventStatus; metadata:Record<string, unknown>; };
export type RetrievedDocument = { id:string; source:string; chunk:number; score:number; text:string; metadata:Record<string,string>; x:number; y:number; };
export type ExecutionResult = { executionId:string; answer:string; tokens:string[]; tokenCount:number; embedding:number[]; embeddingDimensions:number; documents:RetrievedDocument[]; context:string; model:string; mode:"rag"|"direct"; startedAt:number; completedAt:number; };
export type KnowledgeDocument = { id:string; name:string; type:string; text:string; chunks:string[]; status:"Indexed"|"Ready"; createdAt:string; };
