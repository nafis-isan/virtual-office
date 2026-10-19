import asyncio
from io import BytesIO
import json

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


def test_index_upload_splits_and_persists_document_and_embeddings(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
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
