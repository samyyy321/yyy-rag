import os
from uuid import uuid4

import pytest

from src.index.doc_ingestion import ingest_file
from src.infra.milvus_client import get_milvus_client


@pytest.mark.asyncio
async def test_ingest_file_remote():
    if not os.getenv("RUN_API_INTEGRATION"):
        pytest.skip("设置 RUN_API_INTEGRATION=1 才运行远程导入测试")
    if not os.path.exists("./2407.21059v1.pdf"):
        pytest.skip("缺少集成测试文档 2407.21059v1.pdf")

    from src.infra.embedding import get_embedding_model
    embedding_model = get_embedding_model()
    milvus_client = get_milvus_client()
    document_id = str(uuid4())
    knowledge_base_id = str(uuid4())

    count = await ingest_file(
        file_path="./2407.21059v1.pdf",
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
        doc_name="2407.21059v1.pdf",
        doc_type="pdf",
        category="test",
        embedding_model=embedding_model,
        milvus_client=milvus_client,
    )

    assert count > 0
    print(f"导入成功，共 {count} 个分块")
