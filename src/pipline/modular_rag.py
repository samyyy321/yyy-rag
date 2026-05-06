import os

from src.index.indexer import Indexer
from src.query.query_processor import QueryProcessor
from src.query.retriver import Retriever
from src.query.post_processor import PostProcessor
from src.query.generator import Generator


class ModularRAG:
    def __init__(self):
        self.indexer = Indexer()
        self.query_processor = QueryProcessor()
        self.post_processor = PostProcessor()
        self.generator = Generator()

        # 尝试加载已有索引
        try:
            self.index = self.indexer.load_existing_index()
            self.retriever = Retriever(self.index)
        except Exception as e:
            print(f"⚠️ 未能加载已有索引 (可能还未建立): {e}")
            self.index = None
            self.retriever = None

    def load(self, file_path: str):
        """加载文档并构建索引"""
        self.index = self.indexer.index_documents(file_path)
        self.retriever = Retriever(self.index)

    def query(self, query_str: str, history: list = None):
        """处理查询并生成回答"""
        if not self.retriever:
            return {"answer": "请先加载文档构建索引！", "sources": []}

        print("\n[1/4] 开始处理查询...")
        processed_query = self.query_processor.process(query_str, history)

        print("[2/4] 开始检索文档...")
        nodes = self.retriever.retrieve(processed_query)

        print("[3/4] 开始后处理(重排/过滤)...")
        processed_nodes = self.post_processor.process(nodes, processed_query["rewritten"])

        print("[4/4] 开始生成回答...")
        response = self.generator.generate_with_sources(processed_query["rewritten"], processed_nodes)
        return response