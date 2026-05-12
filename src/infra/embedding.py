from http import HTTPStatus
import asyncio

import dashscope
from langchain_core.embeddings import Embeddings
from src.core.config import get_settings


class DashScopeEmbeddings(Embeddings):
    def __init__(self, api_key: str, model: str = "qwen3.7-text-embedding"):
        dashscope.api_key = api_key
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        resp = dashscope.TextEmbedding.call(
            model=self.model,
            input=texts,
        )

        if resp.status_code != HTTPStatus.OK:
            raise ValueError(f"DashScope embedding failed: {resp}")

        return [item["embedding"] for item in resp.output["embeddings"]]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_documents, texts)

    async def aembed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self.embed_query, text)
    
def get_embedding_model():
    return DashScopeEmbeddings(api_key=get_settings().API_KEY, model=get_settings().EMBEDDING_MODEL)
    