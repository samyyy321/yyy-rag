import pytest

from src.index.doc_ingestion import ingest_file
from src.core.config import get_settings
from src.infra.embedding import get_embedding_model
from src.infra.milvus_client import get_milvus_client


@pytest.mark.asyncio
async def test_ingest_file_remote():

    embedding_model = get_embedding_model()
    milvus_client = get_milvus_client()

    count = await ingest_file(
        file_path="./2407.21059v1.pdf",
        doc_name="2407.21059v1.pdf",
        doc_type="pdf",
        category="test",
        embedding_model=embedding_model,
        milvus_client=milvus_client,
    )

    assert count > 0
    print(f"导入成功，共 {count} 个分块")