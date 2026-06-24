"""按知识库隔离执行文档检索和 RAG 回答。"""

from __future__ import annotations

from loguru import logger
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from pymilvus import MilvusClient

from src.core.config import get_settings
from src.query.prompts import DOC_QA_PROMPT


settings = get_settings()
COLLECTION_NAME = settings.MILVUS_COLLECTION_NAME


async def search_docs_raw(
    question: str,
    embedding_model: Embeddings,
    milvus_client: MilvusClient,
    top_k: int = 20,
    rerank_top_k: int = 5,
    doc_type: str | None = None,
    llm: BaseChatModel | None = None,
    use_hyde: bool = False,
    knowledge_base_id: str | None = None,
) -> list[dict]:
    """执行向量检索，并可按知识库和文档类型组合过滤。"""
    if use_hyde and llm is not None:
        from src.query.hyde import generate_hyde_embedding

        query_vec = await generate_hyde_embedding(question, llm, embedding_model)
    else:
        query_vec = await embedding_model.aembed_query(question)

    filters: list[str] = []
    if knowledge_base_id:
        filters.append(f'knowledge_base_id == "{knowledge_base_id}"')
    if doc_type:
        filters.append(f'doc_type == "{doc_type}"')
    filter_expr = " && ".join(filters) if filters else None

    try:
        results = milvus_client.search(
            collection_name=COLLECTION_NAME,
            data=[query_vec],
            limit=top_k,
            output_fields=[
                "knowledge_base_id",
                "doc_id",
                "doc_name",
                "doc_type",
                "category",
                "page_number",
                "chunk_index",
                "text",
            ],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 16}},
            filter=filter_expr,
        )
    except Exception as exc:
        logger.warning(f"文档检索失败: {exc}")
        return []

    if not results or not results[0]:
        return []

    hits = [
        {**hit["entity"], "score": hit.get("distance", 0.0)}
        for hit in results[0]
    ]
    from src.query.reranker import rerank_docs

    return await rerank_docs(question, hits, top_k=rerank_top_k)


def format_doc_context(hits: list[dict]) -> str:
    """将检索结果格式化为 LLM 可读的上下文字符串。"""
    if not hits:
        return ""
    parts = []
    for index, hit in enumerate(hits, 1):
        # 文档定位信息只供检索链路使用，不传给模型，避免出现在用户回答中。
        parts.append(f"文档片段{index} 【来源：{hit['doc_name']}】：\n{hit['text']}")
    return "\n\n---\n\n".join(parts)


async def search_docs(
    question: str,
    embedding_model: Embeddings,
    milvus_client: MilvusClient,
    llm: BaseChatModel,
    top_k: int = 20,
    rerank_top_k: int = 5,
    doc_type: str | None = None,
    role: str = "patient",
    use_hyde: bool = True,
    knowledge_base_id: str | None = None,
) -> str:
    """执行带知识库过滤的 RAG 检索、重排、增强和回答生成。"""
    hits = await search_docs_raw(
        question,
        embedding_model,
        milvus_client,
        top_k=top_k,
        rerank_top_k=rerank_top_k,
        doc_type=doc_type,
        llm=llm,
        use_hyde=use_hyde,
        knowledge_base_id=knowledge_base_id,
    )
    if not hits:
        return "当前知识库中未找到与您问题相关的文档内容。"

    context = format_doc_context(hits)
    prompt = DOC_QA_PROMPT.format(question=question, context=context, role=role)
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    return response.content
