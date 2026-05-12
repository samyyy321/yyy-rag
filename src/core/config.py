"""项目运行配置。"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Config:
    """集中管理离线索引和在线查询共用的配置。"""

    API_KEY = os.getenv("API_KEY")
    BASE_URL = os.getenv("BASE_URL_CHAT", "https://api.openai.com/v1")

    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5-plus")
    RERANK_MODEL = os.getenv("RERANK_MODEL", "qwen3-rerank")

    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530

    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))
    TOP_K = int(os.getenv("TOP_K", "10"))
    RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))

    # MinerU 是可选解析服务；未部署时由离线流程回退到 LlamaIndex。
    MINERU_API_URL: str = os.getenv("MINERU_API_URL", "https://mineru.net/api/v4")
    MINERU_TOKEN: str = os.getenv("MINERU_TOKEN", "")
    MINERU_MODEL_VERSION: str = os.getenv("MINERU_MODEL_VERSION", "vlm")
    MINERU_POLL_INTERVAL: int = int(os.getenv("MINERU_POLL_INTERVAL", "2"))


@lru_cache
def get_settings() -> Config:
    """返回缓存后的项目配置实例。"""
    return Config()
