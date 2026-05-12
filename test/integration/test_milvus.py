from src.infra.milvus_client import check_milvus_health


def test_milvus_health():
    assert check_milvus_health() is True