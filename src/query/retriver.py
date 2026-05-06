from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.retrievers import VectorIndexRetriever, QueryFusionRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from src.core.config import Config
from typing import List, Dict

class Retriever:
    def __init__(self, index: VectorStoreIndex):
        self.index = index
        self.vector_retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=Config.TOP_K
        )

    def vector_search(self, query: str):
        return self.vector_retriever.retrieve(query)

    def hybrid_search(self, query: str):
        query_fusion_retriever = QueryFusionRetriever(
            [self.vector_retriever],
            similarity_top_k=Config.TOP_K,
            num_queries=3,
            use_async=True,
            verbose=True
        )
        return query_fusion_retriever.retrieve(query)

    def retrieve(self, processed_query: Dict, use_hybrid: bool = True):
        if use_hybrid:
            return self.hybrid_search(processed_query["rewritten"])
        else:
            return self.vector_search(processed_query["rewritten"])
