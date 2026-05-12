from loguru import logger
from pymilvus import MilvusClient

from src.core.config import get_settings

settings = get_settings()


def get_milvus_client() -> MilvusClient:
    client = MilvusClient(
        uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
    )
    return client


def check_milvus_health() -> bool:
    client = get_milvus_client()
    client.list_collections()
    logger.info("Milvus 连接成功")
    return True