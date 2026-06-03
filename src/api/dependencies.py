"""FastAPI 依赖注入函数。"""

from collections.abc import Generator
from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from pymilvus import MilvusClient
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.infra.minio_client import ObjectStorage, get_object_storage
from src.infra.milvus_client import get_milvus_client


def get_database() -> Generator[Session, None, None]:
    """为 API 请求提供数据库 Session。"""
    yield from get_db()


@lru_cache
def get_storage() -> ObjectStorage:
    """提供可复用的 MinIO 对象存储适配器。"""
    return get_object_storage()


@lru_cache
def get_milvus() -> MilvusClient:
    """提供可复用的 Milvus 客户端。"""
    return get_milvus_client()


@lru_cache
def get_embedding() -> Embeddings:
    """延迟创建并复用 Embedding 模型。"""
    from src.infra.embedding import get_embedding_model

    return get_embedding_model()


@lru_cache
def get_chat_model() -> BaseChatModel:
    """延迟创建并复用聊天模型。"""
    from src.infra.llm import get_llm

    return get_llm()
