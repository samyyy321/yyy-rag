import pytest

from src.query.doc_rag import search_docs_raw, search_docs
from src.infra.embedding import get_embedding_model
from src.infra.milvus_client import get_milvus_client
from src.infra.llm import get_llm


@pytest.mark.asyncio
async def test_search_docs_raw():
    embedding_model = get_embedding_model()
    milvus_client = get_milvus_client()
    llm = get_llm()

    hits = await search_docs_raw(
        question="什么是Transformer？",
        embedding_model=embedding_model,
        milvus_client=milvus_client,
        top_k=20,
        rerank_top_k=5,
        llm=llm,
    )

    print("\n检索结果:")
    for i, hit in enumerate(hits, 1):
        print(f"{i}. {hit['doc_name']} - {hit['text'][:100]}")

    assert len(hits) > 0
    assert len(hits) <= 5