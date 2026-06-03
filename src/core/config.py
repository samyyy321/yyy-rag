"""项目运行配置。"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Config:
    """集中管理 RAG、生产 API 和评测流程共用的配置。"""

    API_KEY = os.getenv("API_KEY")
    BASE_URL = os.getenv("BASE_URL_CHAT", "https://api.openai.com/v1")

    # 生产业务数据库与 TruLens 评测数据库严格分离。
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://rag:rag@localhost:5432/rag",
    )
    TRULENS_DATABASE_URL = os.getenv("TRULENS_DATABASE_URL")

    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5-plus")
    RERANK_MODEL = os.getenv("RERANK_MODEL", "qwen3-rerank")

    # Milvus：生产 API 默认使用带知识库隔离字段的版本化 collection。
    MILVUS_URI: str = os.getenv("MILVUS_URI", "http://localhost:19530")
    MILVUS_COLLECTION_NAME: str = os.getenv(
        "MILVUS_COLLECTION_NAME",
        "knowledge_docs_v2",
    )
    MILVUS_DIM: int = int(os.getenv("MILVUS_DIM", "1024"))
    # 保留旧字段，兼容现有非 API 测试和脚本。
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))

    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))
    TOP_K = int(os.getenv("TOP_K", "10"))
    RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))

    # MinerU 是可选解析服务；未部署时由离线流程回退到 LlamaIndex。
    MINERU_API_URL: str = os.getenv("MINERU_API_URL", "https://mineru.net/api/v4")
    MINERU_TOKEN: str = os.getenv("MINERU_TOKEN", "")
    MINERU_MODEL_VERSION: str = os.getenv("MINERU_MODEL_VERSION", "vlm")
    MINERU_POLL_INTERVAL: int = int(os.getenv("MINERU_POLL_INTERVAL", "2"))

    # MinIO 原始文档存储配置。
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "rag-documents")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"


@lru_cache
def get_settings() -> Config:
    """返回缓存后的项目配置实例。"""
    return Config()
