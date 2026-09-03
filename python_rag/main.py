"""Real Python RAG service used by the Next.js proxy.

Run locally with: uvicorn python_rag.main:app --reload --port 8001
The service refuses to claim live retrieval when credentials are absent.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Iterator

import tiktoken
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, Field
from pinecone import Pinecone

app = FastAPI(title="RAG AI Chat Studio Python RAG Service", version="1.0.0")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "rag-chat-studio")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "knowledge-base")


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    mode: str = Field(default="rag", pattern="^(rag|direct)$")
    history: list[dict[str, str]] = Field(default_factory=list)


def event(execution_id: str, name: str, stage: str, status: str, **metadata: Any) -> dict[str, Any]:
    return {"executionId": execution_id, "timestamp": datetime.now(timezone.utc).isoformat(), "name": name, "stage": stage, "status": status, "metadata": metadata}


def tokens_for(text: str) -> list[str]:
    """Use the actual OpenAI tokenizer for the configured model where available."""
    try:
        encoder = tiktoken.encoding_for_model(LLM_MODEL)
    except KeyError:
        encoder = tiktoken.get_encoding("cl100k_base")
    token_ids = encoder.encode(text)
    return [encoder.decode_single_token_bytes(token_id).decode("utf-8", errors="replace") for token_id in token_ids]


def chunks_for(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    if size <= overlap:
        raise ValueError("Chunk size must be greater than overlap")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


def clients() -> tuple[OpenAI, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for the Python live RAG service")
    if not os.getenv("PINECONE_API_KEY"):
        raise RuntimeError("PINECONE_API_KEY is required for the Python live RAG service")
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"]), Pinecone(api_key=os.environ["PINECONE_API_KEY"]).Index(PINECONE_INDEX)


def embed(openai_client: OpenAI, text: str) -> list[float]:
    response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def retrieve(index: Any, vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
    response = index.query(vector=vector, top_k=top_k, namespace=PINECONE_NAMESPACE, include_metadata=True)
    matches = []
    for match in response.matches:
        metadata = dict(match.metadata or {})
        matches.append({"id": match.id, "source": str(metadata.get("source", "Unknown source")), "chunk": int(metadata.get("chunk", 0)), "score": round(float(match.score or 0), 4), "text": str(metadata.get("text", "")), "metadata": {str(key): str(value) for key, value in metadata.items()}, "x": 50, "y": 50})
    return matches


def answer_stream(openai_client: OpenAI, prompt: str, context: str, history: list[dict[str, str]]) -> Iterator[str]:
    system = "Answer the user using the retrieved context when provided. Cite source names from context. Do not reveal hidden chain-of-thought."
    messages = [{"role": "system", "content": system}, *history[-10:], {"role": "user", "content": f"USER PROMPT:\n{prompt}\n\nRETRIEVED CONTEXT:\n{context}"}]
    response = openai_client.chat.completions.create(model=LLM_MODEL, messages=messages, stream=True)
    for part in response:
        token = part.choices[0].delta.content if part.choices else None
        if token:
            yield token


def stream_chat(request: ChatRequest) -> Iterator[str]:
    execution_id = f"exec_{uuid.uuid4().hex[:12]}"
    started = time.perf_counter()
    try:
        openai_client, index = clients()
        yield f"data: {json.dumps(event(execution_id, 'execution.started', 'prompt', 'running', mode=request.mode, provider='python'))}\n\n"
        prompt_tokens = tokens_for(request.prompt)
        yield f"data: {json.dumps(event(execution_id, 'prompt.received', 'prompt', 'completed', prompt=request.prompt, characters=len(request.prompt)))}\n\n"
        yield f"data: {json.dumps(event(execution_id, 'tokenization.completed', 'tokens', 'completed', tokens=prompt_tokens, tokenCount=len(prompt_tokens), tokenizer='tiktoken', estimated=False))}\n\n"
        should_retrieve = request.mode == "rag" and not re.fullmatch(r"\s*what is \d+\s*[+*x-]\s*\d+\s*\??\s*", request.prompt.lower())
        yield f"data: {json.dumps(event(execution_id, 'agent.decision', 'agent', 'completed', retrievalRequired=should_retrieve, reason='Knowledge question benefits from grounding' if should_retrieve else 'Direct calculation does not need retrieval'))}\n\n"
        vector: list[float] = []
        documents: list[dict[str, Any]] = []
        context = ""
        if should_retrieve:
            yield f"data: {json.dumps(event(execution_id, 'embedding.started', 'embedding', 'running', model=EMBEDDING_MODEL))}\n\n"
            vector = embed(openai_client, request.prompt)
            yield f"data: {json.dumps(event(execution_id, 'embedding.completed', 'embedding', 'completed', model=EMBEDDING_MODEL, dimensions=len(vector), preview=vector[:4]))}\n\n"
            yield f"data: {json.dumps(event(execution_id, 'vector.search.started', 'search', 'running', index=PINECONE_INDEX, namespace=PINECONE_NAMESPACE, topK=5))}\n\n"
            documents = retrieve(index, vector)
            yield f"data: {json.dumps(event(execution_id, 'vector.search.completed', 'search', 'completed', results=len(documents), scores=[item['score'] for item in documents], provider='pinecone'))}\n\n"
            context = "\n\n".join(f"[{number}] {item['source']}\n{item['text']}" for number, item in enumerate(documents, 1))
            yield f"data: {json.dumps(event(execution_id, 'context.completed', 'context', 'completed', chunks=len(documents), characters=len(context)))}\n\n"
        yield f"data: {json.dumps(event(execution_id, 'llm.started', 'llm', 'running', model=LLM_MODEL))}\n\n"
        answer = ""
        for token in answer_stream(openai_client, request.prompt, context, request.history):
            answer += token
            yield f"data: {json.dumps(event(execution_id, 'llm.token', 'llm', 'running', token=token))}\n\n"
        duration_ms = round((time.perf_counter() - started) * 1000)
        yield f"data: {json.dumps(event(execution_id, 'llm.completed', 'llm', 'completed', outputTokens=len(tokens_for(answer))))}\n\n"
        yield f"data: {json.dumps(event(execution_id, 'execution.completed', 'answer', 'completed', durationMs=duration_ms))}\n\n"
        result = {"type": "result", "result": {"executionId": execution_id, "answer": answer, "tokens": prompt_tokens, "tokenCount": len(prompt_tokens), "embedding": vector, "embeddingDimensions": len(vector), "documents": documents, "context": context, "model": LLM_MODEL, "mode": request.mode, "startedAt": int(started * 1000), "completedAt": int(started * 1000) + duration_ms}}
        yield f"data: {json.dumps(result)}\n\n"
    except Exception as error:
        failure = event(execution_id, "execution.failed", "answer", "failed", error=str(error), provider="python")
        yield f"data: {json.dumps(failure)}\n\n"


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "provider": "python", "openaiConfigured": bool(os.getenv("OPENAI_API_KEY")), "pineconeConfigured": bool(os.getenv("PINECONE_API_KEY")), "embeddingModel": EMBEDDING_MODEL, "llmModel": LLM_MODEL}


@app.post("/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(stream_chat(request), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


@app.post("/index")
async def index_document(file: UploadFile) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith((".txt", ".md", ".pdf")):
        raise HTTPException(status_code=415, detail="Only TXT, Markdown, and PDF files are supported")
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB limit")
    if file.filename.lower().endswith(".pdf"):
        from pypdf import PdfReader
        import io
        text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(contents)).pages)
    else:
        text = contents.decode("utf-8", errors="replace")
    openai_client, index = clients()
    chunks = chunks_for(text)
    vectors = [{"id": f"{uuid.uuid4().hex}-{number}", "values": embed(openai_client, chunk), "metadata": {"source": file.filename, "chunk": number, "text": chunk}} for number, chunk in enumerate(chunks, 1)]
    index.upsert(vectors=vectors, namespace=PINECONE_NAMESPACE)
    return {"source": file.filename, "characters": len(text), "chunks": len(chunks), "embeddings": len(vectors), "indexed": len(vectors), "embeddingDimensions": len(vectors[0]["values"]) if vectors else 0}
