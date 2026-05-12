"""查询流程编排。离线索引请直接调用 src.index.doc_ingestion.ingest_file。"""

from src.query.query_processor import QueryProcessor
from src.query.retriver import Retriever
from src.query.post_processor import PostProcessor
from src.query.generator import Generator


class ModularRAG:
    """负责在线查询编排，不再拥有独立的离线索引构建器。"""

    def __init__(self):
        self.query_processor = QueryProcessor()
        self.post_processor = PostProcessor()
        self.generator = Generator()
        self.index = None
        self.retriever = None

    def query(self, query_str: str, history: list | None = None):
        """处理查询并生成带来源的回答。"""
        if not self.retriever:
            return {"answer": "请先完成离线索引并配置查询检索器。", "sources": []}

        processed_query = self.query_processor.process(query_str, history)
        nodes = self.retriever.retrieve(processed_query)
        processed_nodes = self.post_processor.process(nodes, processed_query["rewritten"])
        return self.generator.generate_with_sources(processed_query["rewritten"], processed_nodes)
