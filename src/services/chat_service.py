"""按知识库执行 RAG 问答和基础依赖健康检查。"""

from __future__ import annotations

from uuid import UUID

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from pymilvus import MilvusClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from loguru import logger

from src.api.schemas import ChatResponse, ChatSource
from src.db.models import KnowledgeBase
from src.infra.minio_client import ObjectStorage
from src.query.doc_rag import format_doc_context, search_docs_raw
from src.query.prompts import DOC_QA_PROMPT
from src.services.errors import ResourceNotFoundError


async def generate_answer(
    *,
    question: str,
    context: str,
    role: str,
    llm: BaseChatModel,
) -> str:
    """使用现有生产提示词和模型生成回答。"""
    prompt = DOC_QA_PROMPT.format(question=question, context=context, role=role)
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    return response.content if isinstance(response.content, str) else str(response.content)


async def answer_question(
    *,
    knowledge_base_id: UUID,
    question: str,
    role: str,
    top_k: int,
    rerank_top_k: int,
    use_hyde: bool,
    db: Session,
    embedding_model: Embeddings,
    milvus_client: MilvusClient,
    llm: BaseChatModel,
) -> ChatResponse:
    """校验知识库后只在该知识库范围内检索并生成回答。"""
    exists = db.execute(
        select(KnowledgeBase.id).where(KnowledgeBase.id == knowledge_base_id)
    ).scalar_one_or_none()
    if exists is None:
        raise ResourceNotFoundError("知识库不存在")

    hits = await search_docs_raw(
        question=question,
        embedding_model=embedding_model,
        milvus_client=milvus_client,
        top_k=top_k,
        rerank_top_k=rerank_top_k,
        llm=llm,
        use_hyde=use_hyde,
        knowledge_base_id=str(knowledge_base_id),
    )
    if not hits:
        return ChatResponse(answer="当前知识库中未找到与您问题相关的文档内容。", sources=[])

    answer = await generate_answer(
        question=question,
        context=format_doc_context(hits),
        role=role,
        llm=llm,
    )
    sources = [
        ChatSource(
            document_id=UUID(hit["doc_id"]),
            document_name=hit["doc_name"],
            page_number=int(hit.get("page_number", 0)),
            chunk_index=int(hit.get("chunk_index", 0)),
            score=float(hit.get("rerank_score", hit.get("score", 0.0))),
            text=hit["text"],
        )
        for hit in hits
    ]
    return ChatResponse(answer=answer, sources=sources)


def check_health(
    db: Session,
    storage: ObjectStorage,
    milvus_client: MilvusClient,
) -> bool:
    """检查 PostgreSQL、MinIO bucket 和 Milvus 的基础连通性。"""
    try:
        db.execute(text("SELECT 1"))
        storage.ensure_bucket()
        milvus_client.list_collections()
        return True
    except Exception as exc:
        logger.warning(f"健康检查失败: {exc}")
        return False
