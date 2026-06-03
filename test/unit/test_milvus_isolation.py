from unittest.mock import Mock

import pytest

from src.index.doc_ingestion import ensure_knowledge_collection
from src.query.doc_rag import search_docs_raw


def test_collection_schema_contains_knowledge_base_id():
    client = Mock()
    client.has_collection.return_value = False

    ensure_knowledge_collection(client)

    schema = client.create_collection.call_args.kwargs["schema"]
    field_names = {field["name"] for field in schema.to_dict()["fields"]}
    assert field_names == {
        "id", "knowledge_base_id", "doc_id", "doc_name", "doc_type",
        "category", "page_number", "chunk_index", "text", "embedding",
    }
    assert client.create_collection.call_args.kwargs["collection_name"] == "knowledge_docs_v2"


@pytest.mark.asyncio
async def test_search_filter_contains_knowledge_base_id():
    client = Mock()
    client.search.return_value = [[]]

    class Embedding:
        async def aembed_query(self, question):
            return [0.1, 0.2]

    result = await search_docs_raw(
        question="q",
        embedding_model=Embedding(),
        milvus_client=client,
        knowledge_base_id="kb-1",
        top_k=5,
        rerank_top_k=1,
    )

    assert result == []
    assert client.search.call_args.kwargs["filter"] == 'knowledge_base_id == "kb-1"'
    assert "knowledge_base_id" in client.search.call_args.kwargs["output_fields"]
    assert "doc_id" in client.search.call_args.kwargs["output_fields"]
