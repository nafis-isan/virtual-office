import asyncio
from io import BytesIO
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.datastructures import Headers, UploadFile

from app.db.base import Base
from app.models import KnowledgeChunk, KnowledgeDocument
from app.services import knowledge


def test_split_text_creates_overlapping_chunks_with_page_numbers():
    text = "kata " * 600

    chunks = knowledge._split_text(text, page_number=3)

    assert len(chunks) > 1
    assert all(chunk.page_number == 3 for chunk in chunks)
    assert chunks[0].content[-30:] in chunks[1].content


def test_retrieve_context_ranks_relevant_chunks_and_omits_weak_matches(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(knowledge.settings, "ai_provider", "gemini")
    monkeypatch.setattr(knowledge.settings, "gemini_api_key", "test-key")
    with Session(engine) as db:
        relevant = KnowledgeDocument(filename="panduan.md", content_type="text/markdown", chunk_count=1)
        relevant.chunks = [
            KnowledgeChunk(content="Kebijakan kerja jarak jauh.", embedding=json.dumps([1.0, 0.0]))
        ]
        unrelated = KnowledgeDocument(filename="menu.md", content_type="text/markdown", chunk_count=1)
        unrelated.chunks = [
            KnowledgeChunk(content="Daftar menu makan siang.", embedding=json.dumps([0.0, 1.0]))
        ]
        db.add_all([relevant, unrelated])
        db.commit()
        monkeypatch.setattr(knowledge, "embed_texts", lambda *_args, **_kwargs: [[1.0, 0.0]])

        results = knowledge.retrieve_context(db, "kebijakan kerja jarak jauh")

    assert len(results) == 1
    assert results[0].filename == "panduan.md"
    assert results[0].content == "Kebijakan kerja jarak jauh."
    assert results[0].citation == "panduan.md"


def test_retrieve_context_skips_gemini_when_openrouter_has_no_embedding_key(
    monkeypatch,
):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(knowledge.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(knowledge.settings, "gemini_api_key", "")
    monkeypatch.setattr(
        knowledge,
        "embed_texts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Gemini embeddings must not be called")
        ),
    )

    with Session(engine) as db:
        document = KnowledgeDocument(
            filename="panduan.md",
            content_type="text/markdown",
            chunk_count=1,
        )
        document.chunks = [
            KnowledgeChunk(content="Aturan internal.", embedding=json.dumps([1.0, 0.0]))
        ]
        db.add(document)
        db.commit()

        results = knowledge.retrieve_context(db, "aturan internal")

    assert len(results) == 1
    assert results[0].filename == "panduan.md"
    assert results[0].score == 1.0


def test_index_upload_splits_and_persists_document_and_embeddings(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(knowledge.settings, "ai_provider", "gemini")
    monkeypatch.setattr(knowledge.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(
        knowledge,
        "embed_texts",
        lambda texts, **_kwargs: [[float(len(text)), 1.0] for text in texts],
    )
    upload = UploadFile(
        BytesIO(("Kebijakan kerja. " * 180).encode()),
        filename="kebijakan.txt",
        headers=Headers({"content-type": "text/plain"}),
    )

    with Session(engine) as db:
        document = asyncio.run(knowledge.index_upload(db, upload))
        stored = db.get(KnowledgeDocument, document.id)

        assert stored is not None
        assert stored.filename == "kebijakan.txt"
        assert stored.chunk_count > 1
        assert len(stored.chunks) == stored.chunk_count
        assert all(json.loads(chunk.embedding) for chunk in stored.chunks)


def test_openrouter_indexes_documents_without_gemini_embeddings(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(knowledge.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(knowledge.settings, "gemini_api_key", "")
    monkeypatch.setattr(
        knowledge,
        "embed_texts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Gemini embeddings must not be called")
        ),
    )
    upload = UploadFile(
        BytesIO(b"Cuaca Jakarta dan prakiraan hujan."),
        filename="dokumen.txt",
        headers=Headers({"content-type": "text/plain"}),
    )

    with Session(engine) as db:
        document = asyncio.run(knowledge.index_upload(db, upload))
        stored_chunk = db.get(KnowledgeChunk, document.chunks[0].id)

        assert stored_chunk is not None
        assert json.loads(stored_chunk.embedding) == []
        results = knowledge.retrieve_context(db, "prakiraan cuaca Jakarta")

    assert len(results) == 1
    assert results[0].filename == "dokumen.txt"


def test_gemini_provider_still_requires_api_key_for_document_embeddings(monkeypatch):
    monkeypatch.setattr(knowledge.settings, "ai_provider", "gemini")
    monkeypatch.setattr(knowledge.settings, "gemini_api_key", "")
    upload = UploadFile(
        BytesIO(b"Dokumen"),
        filename="dokumen.txt",
        headers=Headers({"content-type": "text/plain"}),
    )

    with Session(create_engine("sqlite://")) as db:
        with pytest.raises(HTTPException, match="GEMINI_API_KEY") as error:
            asyncio.run(knowledge.index_upload(db, upload))
        assert error.value.status_code == 503
