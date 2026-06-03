"""Milvus 客户端创建和基础健康检查。"""

from loguru import logger
from pymilvus import MilvusClient

from src.core.config import get_settings


def get_milvus_client() -> MilvusClient:
    """根据生产配置创建 Milvus 客户端。"""
    return MilvusClient(uri=get_settings().MILVUS_URI)


def check_milvus_health() -> bool:
    """检查 Milvus 是否可以列出 collection。"""
    client = get_milvus_client()
    client.list_collections()
    logger.info("Milvus 连接成功")
    return True
