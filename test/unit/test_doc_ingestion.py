from unittest.mock import Mock

import pytest

from src.index import doc_ingestion
from src.index.chunking import ChunkSegment, SourceSegment


@pytest.mark.asyncio
async def test_ingest_file_passes_mineru_text_and_selected_strategy_to_splitter(monkeypatch):
    """MinerU 文本应成为页码 0 源单元，并使用用户选择的策略切分。"""
    captured = {}
    milvus = Mock()

    async def split_source_segments(source_segments, **kwargs):
        captured["source_segments"] = source_segments
        captured["kwargs"] = kwargs
        return [ChunkSegment(text="切分结果", page_number=0)]

    async def parse_mineru(_file_path, _doc_name):
        return "MinerU 文本"

    embedding = Mock()
    embedding.aembed_documents = Mock(return_value=None)

    async def embed_documents(texts):
        return [[0.1] for _ in texts]

    embedding.aembed_documents = embed_documents
    monkeypatch.setattr(doc_ingestion, "ensure_knowledge_collection", lambda _client: None)
    monkeypatch.setattr(doc_ingestion, "_parse_with_mineru", parse_mineru)
    monkeypatch.setattr(doc_ingestion, "split_source_segments", split_source_segments)

    count = await doc_ingestion.ingest_file(
        file_path="unused.md",
        document_id="doc-1",
        knowledge_base_id="kb-1",
        doc_name="a.md",
        doc_type="md",
        category="default",
        embedding_model=embedding,
        milvus_client=milvus,
        chunk_strategy="sliding_window",
    )

    assert count == 1
    assert captured["source_segments"] == [SourceSegment(text="MinerU 文本", page_number=0)]
    assert captured["kwargs"]["strategy"] == "sliding_window"
    assert milvus.insert.call_args.kwargs["data"][0]["page_number"] == 0


def test_build_llama_source_segments_keeps_page_label():
    """LlamaIndex 解析单元必须保留其 page_label 页码。"""
    document = Mock()
    document.get_content.return_value = "第二页内容"
    document.metadata = {"page_label": "2"}

    segments = doc_ingestion._build_llama_source_segments([document])

    assert segments == [SourceSegment(text="第二页内容", page_number=2)]
