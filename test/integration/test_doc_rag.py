import os

import pytest

from src.query.doc_rag import search_docs_raw
from src.infra.milvus_client import get_milvus_client


@pytest.mark.asyncio
async def test_search_docs_raw():
    if not os.getenv("RUN_API_INTEGRATION"):
        pytest.skip("设置 RUN_API_INTEGRATION=1 才运行远程检索测试")
    knowledge_base_id = os.getenv("TEST_KNOWLEDGE_BASE_ID")
    if not knowledge_base_id:
        pytest.skip("设置 TEST_KNOWLEDGE_BASE_ID 指向已导入的测试知识库")

    from src.infra.embedding import get_embedding_model
    from src.infra.llm import get_llm
    hits = await search_docs_raw(
        question="什么是Transformer？",
        embedding_model=get_embedding_model(),
        milvus_client=get_milvus_client(),
        top_k=20,
        rerank_top_k=5,
        llm=get_llm(),
        knowledge_base_id=knowledge_base_id,
    )

    print("\n检索结果:")
    for i, hit in enumerate(hits, 1):
        print(f"{i}. {hit['doc_name']} - {hit['text'][:100]}")

    assert len(hits) > 0
    assert len(hits) <= 5
    assert all(hit["knowledge_base_id"] == knowledge_base_id for hit in hits)
