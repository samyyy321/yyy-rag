"""文档解析、策略切分、Embedding 和 Milvus v2 写入流程。"""

from __future__ import annotations

from typing import Any

from langchain_core.embeddings import Embeddings
from loguru import logger
from pymilvus import DataType, MilvusClient

from src.core.config import get_settings
from src.index.chunking import ChunkStrategy, SourceSegment, split_source_segments


settings = get_settings()
COLLECTION_NAME = settings.MILVUS_COLLECTION_NAME
EMBEDDING_DIM = settings.MILVUS_DIM
CHUNK_SIZE = settings.CHUNK_SIZE
CHUNK_OVERLAP = settings.CHUNK_OVERLAP
SEMANTIC_SIMILARITY_THRESHOLD = settings.SEMANTIC_SIMILARITY_THRESHOLD


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


async def _parse_with_llamaindex(file_path: str) -> list[Any]:
    """使用 LlamaIndex 作为文档解析兜底方案。"""
    from llama_index.core import SimpleDirectoryReader

    reader = SimpleDirectoryReader(input_files=[file_path])
    return reader.load_data()


def _build_mineru_source_segments(md_text: str) -> list[SourceSegment]:
    """将 MinerU Markdown 转为当前无法定位页码的单一源单元。"""
    text = md_text.strip()
    return [SourceSegment(text=text, page_number=0)] if text else []


def _build_llama_source_segments(documents: list[Any]) -> list[SourceSegment]:
    """将 LlamaIndex 文档单元转为保留 page_label 的切分源单元。"""
    source_segments: list[SourceSegment] = []
    for document in documents:
        get_content = getattr(document, "get_content", None)
        source_text = get_content() if callable(get_content) else getattr(document, "text", "")
        text = str(source_text).strip()
        if not text:
            continue

        metadata = getattr(document, "metadata", {}) or {}
        page_number = _parse_page_number(metadata.get("page_label", 0))
        source_segments.append(SourceSegment(text=text, page_number=page_number))
    return source_segments


def _parse_page_number(value: object) -> int:
    """将解析器页码转换为整数，缺失或无效值统一回退为 0。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


async def ingest_file(
    file_path: str,
    document_id: str,
    knowledge_base_id: str,
    doc_name: str,
    doc_type: str,
    category: str,
    embedding_model: Embeddings,
    milvus_client: MilvusClient,
    chunk_strategy: ChunkStrategy = "recursive",
) -> int:
    """解析文档，按持久化策略切分、向量化并写入知识库隔离的 Milvus。"""
    ensure_knowledge_collection(milvus_client)
    milvus_client.delete(
        collection_name=COLLECTION_NAME,
        filter=(
            f'knowledge_base_id == "{knowledge_base_id}" '
            f'&& doc_id == "{document_id}"'
        ),
    )

    # MinerU 和 LlamaIndex 最终都进入同一个策略分发器，策略不再依赖解析路径。
    md_text = await _parse_with_mineru(file_path, doc_name)
    if md_text:
        source_segments = _build_mineru_source_segments(md_text)
    else:
        source_segments = _build_llama_source_segments(
            await _parse_with_llamaindex(file_path)
        )

    if not source_segments:
        logger.warning(f"文档 '{doc_name}' 解析后无内容")
        return 0

    chunks = await split_source_segments(
        source_segments,
        strategy=chunk_strategy,
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP,
        semantic_similarity_threshold=SEMANTIC_SIMILARITY_THRESHOLD,
        embedding_model=embedding_model,
    )
    if not chunks:
        logger.warning(f"文档 '{doc_name}' 切分后无内容")
        return 0

    all_data: list[dict[str, object]] = []
    for start in range(0, len(chunks), 20):
        batch_chunks = chunks[start:start + 20]
        embeddings = await embedding_model.aembed_documents(
            [chunk.text for chunk in batch_chunks]
        )
        for offset, (chunk, embedding) in enumerate(zip(batch_chunks, embeddings, strict=True)):
            chunk_index = start + offset
            all_data.append(
                {
                    "id": f"{document_id}_{chunk_index}",
                    "knowledge_base_id": knowledge_base_id,
                    "doc_id": document_id,
                    "doc_name": doc_name,
                    "doc_type": doc_type,
                    "category": category,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk_index,
                    "text": chunk.text[:65000],
                    "embedding": embedding,
                }
            )

    milvus_client.insert(collection_name=COLLECTION_NAME, data=all_data)
    logger.info(
        f"文档 '{doc_name}' 使用 {chunk_strategy} 策略导入完成，共 {len(all_data)} 个分块"
    )
    return len(all_data)
