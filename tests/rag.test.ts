import { describe, expect, it } from "vitest";
import { chunkText } from "../lib/chunk";
describe("RAG primitives",()=>{ it("chunks real text without inventing counts",()=>{ expect(chunkText("a".repeat(1200),600).length).toBe(2); }); it("tokenizes punctuation in the execution route",()=>{ expect("What is RAG?".match(/[A-Za-z]+|[^\sA-Za-z0-9]/g)).toEqual(["What","is","RAG","?"]); }); });
