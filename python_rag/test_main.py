from python_rag.main import chunks_for, tokens_for


def test_chunks_have_overlap_and_cover_input():
    text = "a" * 1600
    chunks = chunks_for(text, size=800, overlap=120)
    assert len(chunks) == 3
    assert "a" * 120 in chunks[0] and "a" * 120 in chunks[1]


def test_tokenizer_returns_actual_model_tokens():
    tokens = tokens_for("What is RAG?")
    assert tokens
    assert "RAG" in "".join(tokens)
