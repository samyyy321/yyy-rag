from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.schema import NodeWithScore
from llama_index.postprocessor.dashscope_rerank import DashScopeRerank

from src.core.config import Config
from typing import List

class PostProcessor:
    def __init__(self):
        self.similarity_filter = SimilarityPostprocessor(similarity_cutoff=0.7)
        self.reranker = None
        if Config.API_KEY:
            try:
                self.reranker = DashScopeRerank(
                    api_key=Config.API_KEY,
                    top_n=Config.RERANK_TOP_N,
                    model=Config.RERANK_MODEL,
                )
            except Exception as e:
                print(f"❌️ DashScope reranker模型:{Config.RERANK_MODEL} 初始化失败: {e}")

    def filter_low_similarity(self, nodes) -> List[NodeWithScore]:
        return self.similarity_filter.postprocess_nodes(nodes)

    def rerank(self, nodes, query: str) -> List[NodeWithScore]:
        if self.reranker:
            return self.reranker.postprocess_nodes(nodes, query_str=query)
        return nodes[:Config.RERANK_TOP_N]

    def process(self, nodes, query: str) -> List[NodeWithScore]:
        filtered = self.filter_low_similarity(nodes)
        reranked = self.rerank(filtered, query)
        return reranked