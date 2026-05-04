from llama_index.core import  VectorStoreIndex, StorageContext, Settings, Document
from llama_index.core.node_parser import SentenceSplitter, SentenceWindowNodeParser, MarkdownNodeParser
from llama_index.core.schema import BaseNode
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.readers.file import UnstructuredReader
from llama_index.vector_stores.milvus import MilvusVectorStore
from src.core.config import Config


class Indexer:
    def __init__(self):
        Settings.llm = OpenAILike(
            model=Config.LLM_MODEL,
            api_key=Config.API_KEY,
            api_base=Config.BASE_URL,
            is_chat_model=True,
            is_function_calling_model=True,
            timeout=300
        )
        Settings.embed_model = OpenAILikeEmbedding(
            model_name=Config.EMBEDDING_MODEL,
            api_key=Config.API_KEY,
            api_base=Config.BASE_URL,
            timeout=300
        )
        self.vector_store = MilvusVectorStore(
            uri=Config.MILVUS_URI,
            collection_name=Config.MILVUS_COLLECTION_NAME,
            dim=Config.MILVUS_DIM
        )
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def load_documents(self, file: str) -> list[Document]:
        """
        从文件加载文档
        """
        reader = UnstructuredReader()
        return reader.load_data(file=file,split_documents=False)

    def split_documents(self, documents: list[Document]) -> list[BaseNode]:
        """
        将文档拆分成chunks
        """
        # 语义拆分器
        parser = SentenceSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP
        )

        # 语义窗口拆分器
        window_parser = SentenceWindowNodeParser(
            sentence_splitter=parser,
            window_size=3,
            window_metadata_key="window",
            original_text_metadata_key="original_text",
            include_metadata=True,
            include_prev_next_rel=True,
        )

        # markdown 拆分器； 测试各种拆分器的用法
        return MarkdownNodeParser().get_nodes_from_documents(documents=documents,show_progress=True)

    def build_index(self, nodes: list[BaseNode]) -> VectorStoreIndex:
        """
        构建索引
        """
        index = VectorStoreIndex(
            nodes,
            storage_context=self.storage_context,
            show_progress=True
        )
        return index

    def index_documents(self, directory: str):
        print(f"😄从 {directory} 中加载文档...")
        documents = self.load_documents(directory)
        print(f"👌已加载 {len(documents)} 个文档")

        print("🔓开始将文档拆分成段落...")
        nodes = self.split_documents(documents)
        print(f"👌已拆分成 {len(nodes)} 个段落")

        print("📚开始构建索引...")
        index = self.build_index(nodes)
        print("👌索引构建完成!")


        return index

    def load_existing_index(self) -> VectorStoreIndex:
        return VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=self.storage_context
        )