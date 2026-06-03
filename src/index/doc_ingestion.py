"""文档解析、切块、Embedding 和 Milvus v2 写入流程。"""

from __future__ import annotations

from loguru import logger
from langchain_core.embeddings import Embeddings
from pymilvus import DataType, MilvusClient

from src.core.config import get_settings


settings = get_settings()
COLLECTION_NAME = settings.MILVUS_COLLECTION_NAME
EMBEDDING_DIM = settings.MILVUS_DIM
CHUNK_SIZE = settings.CHUNK_SIZE
CHUNK_OVERLAP = settings.CHUNK_OVERLAP


def ensure_knowledge_collection(milvus_client: MilvusClient) -> None:
    """确保带知识库隔离字段的生产 collection 存在。"""
    if milvus_client.has_collection(COLLECTION_NAME):
        return

    schema = MilvusClient.create_schema(auto_id=False)
    schema.add_field("id", DataType.VARCHAR, max_length=256, is_primary=True)
    schema.add_field("knowledge_base_id", DataType.VARCHAR, max_length=128)
    schema.add_field("doc_id", DataType.VARCHAR, max_length=128)
    schema.add_field("doc_name", DataType.VARCHAR, max_length=256)
    schema.add_field("doc_type", DataType.VARCHAR, max_length=50)
    schema.add_field("category", DataType.VARCHAR, max_length=100)
    schema.add_field("page_number", DataType.INT64)
    schema.add_field("chunk_index", DataType.INT64)
    schema.add_field("text", DataType.VARCHAR, max_length=65535)
    schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)

    index_params = MilvusClient.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        metric_type="COSINE",
        index_type="IVF_FLAT",
        params={"nlist": 128},
    )
    milvus_client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=index_params,
    )
    logger.info(f"Collection '{COLLECTION_NAME}' 创建成功")


async def _parse_with_mineru(file_path: str, file_name: str) -> str | None:
    """尝试用 MinerU 解析文档，失败则返回 None。"""
    try:
        from src.index.mineru_client import parse_document

        md_text = await parse_document(file_path)
        if md_text and len(md_text.strip()) > 10:
            logger.info(f"MinerU 解析成功: {file_name} ({len(md_text)} chars)")
            return md_text
    except Exception as exc:
        logger.warning(f"MinerU 解析失败，回退到 LlamaIndex: {exc}")
    return None


async def _parse_with_llamaindex(file_path: str) -> list:
    """使用 LlamaIndex 作为文档解析兜底方案。"""
    from llama_index.core import SimpleDirectoryReader

    reader = SimpleDirectoryReader(input_files=[file_path])
    return reader.load_data()


def _split_markdown(
    md_text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """按段落合并 Markdown，并对超长段落做重叠切分。"""
    paragraphs = md_text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n\n{paragraph}" if current else paragraph
            continue

        if current:
            chunks.append(current)
        if len(paragraph) > chunk_size:
            step = max(1, chunk_size - overlap)
            chunks.extend(paragraph[i:i + chunk_size] for i in range(0, len(paragraph), step))
            current = ""
        else:
            current = paragraph

    if current:
        chunks.append(current)
    return chunks


async def ingest_file(
    file_path: str,
    document_id: str,
    knowledge_base_id: str,
    doc_name: str,
    doc_type: str,
    category: str,
    embedding_model: Embeddings,
    milvus_client: MilvusClient,
) -> int:
    """将指定文档解析、向量化并写入知识库隔离的 Milvus collection。"""
    from llama_index.core.node_parser import SentenceSplitter

    ensure_knowledge_collection(milvus_client)
    milvus_client.delete(
        collection_name=COLLECTION_NAME,
        filter=(
            f'knowledge_base_id == "{knowledge_base_id}" '
            f'&& doc_id == "{document_id}"'
        ),
    )

    # 优先使用 MinerU 解析，失败后回退到 LlamaIndex。
    md_text = await _parse_with_mineru(file_path, doc_name)
    if md_text:
        texts = _split_markdown(md_text)
        pages = [0] * len(texts)
    else:
        documents = await _parse_with_llamaindex(file_path)
        splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        nodes = splitter.get_nodes_from_documents(documents)
        if not nodes:
            logger.warning(f"文档 '{doc_name}' 解析后无内容")
            return 0
        texts = [node.get_content() for node in nodes]
        pages = []
        for node in nodes:
            page = node.metadata.get("page_label", 0)
            try:
                pages.append(int(page))
            except (ValueError, TypeError):
                pages.append(0)

    if not texts:
        return 0

    all_data: list[dict] = []
    for start in range(0, len(texts), 20):
        batch_texts = texts[start:start + 20]
        embeddings = await embedding_model.aembed_documents(batch_texts)
        for offset, (text_content, embedding) in enumerate(zip(batch_texts, embeddings)):
            chunk_index = start + offset
            all_data.append(
                {
                    "id": f"{document_id}_{chunk_index}",
                    "knowledge_base_id": knowledge_base_id,
                    "doc_id": document_id,
                    "doc_name": doc_name,
                    "doc_type": doc_type,
                    "category": category,
                    "page_number": pages[chunk_index] if chunk_index < len(pages) else 0,
                    "chunk_index": chunk_index,
                    "text": text_content[:65000],
                    "embedding": embedding,
                }
            )

    milvus_client.insert(collection_name=COLLECTION_NAME, data=all_data)
    logger.info(f"文档 '{doc_name}' 导入完成，共 {len(all_data)} 个分块")
    return len(all_data)
