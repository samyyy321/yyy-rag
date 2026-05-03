import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("API_KEY")
    BASE_URL = os.getenv("BASE_URL_CHAT", "https://api.openai.com/v1")

    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5-plus")
    RERANK_MODEL = os.getenv("RERANK_MODEL","qwen3-rerank")

    MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
    MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "yyy_rag_docs")
    MILVUS_DIM = os.getenv("MILVUS_DIM", "1024")

    CHUNK_SIZE = 1024
    CHUNK_OVERLAP = 200
    TOP_K = 10
    RERANK_TOP_N = 5