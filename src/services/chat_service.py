"""按知识库执行多通道 RAG 问答和基础依赖健康检查。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from loguru import logger
from pymilvus import MilvusClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.api.schemas import ChatResponse, ChatSource
from src.db.models import KnowledgeBase
from src.infra.minio_client import ObjectStorage
from src.query.channel_types import ChannelEvidence
from src.query.multi_channel import (
    build_answer_prompt,
    collect_evidence,
    generate_channel_answer,
)
from src.services.errors import ResourceNotFoundError


async def answer_question(
    *,
    knowledge_base_id: UUID,
    question: str,
    role: str,
    top_k: int,
    rerank_top_k: int,
    use_hyde: bool,
    channels: list[str] | None = None,
    db: Session,
    embedding_model: Embeddings,
    milvus_client: MilvusClient,
    llm: BaseChatModel,
) -> ChatResponse:
    """校验知识库后执行指定通道的单通道或多通道完整问答。"""
    _ensure_knowledge_base_exists(db, knowledge_base_id)
    evidence = await collect_evidence(
        channels or ["document"],
        knowledge_base_id=knowledge_base_id,
        question=question,
        top_k=top_k,
        rerank_top_k=rerank_top_k,
        use_hyde=use_hyde,
        db=db,
        embedding_model=embedding_model,
        milvus_client=milvus_client,
        llm=llm,
    )
    if not evidence:
        return ChatResponse(answer="当前已选检索通道中未找到相关信息。", sources=[])

    answer = await generate_channel_answer(
        question=question,
        role=role,
        evidence=evidence,
        llm=llm,
    )
    return ChatResponse(answer=answer, sources=_document_sources(evidence))


async def stream_answer(
    *,
    knowledge_base_id: UUID,
    question: str,
    role: str,
    top_k: int,
    rerank_top_k: int,
    use_hyde: bool,
    channels: list[str] | None = None,
    db: Session,
    embedding_model: Embeddings,
    milvus_client: MilvusClient,
    llm: BaseChatModel,
) -> AsyncIterator[str]:
    """按模型生成顺序流式返回指定通道的 RAG 回答文本。"""
    _ensure_knowledge_base_exists(db, knowledge_base_id)
    evidence = await collect_evidence(
        channels or ["document"],
        knowledge_base_id=knowledge_base_id,
        question=question,
        top_k=top_k,
        rerank_top_k=rerank_top_k,
        use_hyde=use_hyde,
        db=db,
        embedding_model=embedding_model,
        milvus_client=milvus_client,
        llm=llm,
    )
    if not evidence:
        yield "当前已选检索通道中未找到相关信息。"
        return

    prompt = build_answer_prompt(question=question, role=role, evidence=evidence)
    async for chunk in llm.astream([SystemMessage(content=prompt)]):
        content = chunk.content
        if isinstance(content, str) and content:
            yield content


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


def _ensure_knowledge_base_exists(db: Session, knowledge_base_id: UUID) -> None:
    """校验指定知识库存在，避免多个通道分别重复校验。"""
    exists = db.execute(
        select(KnowledgeBase.id).where(KnowledgeBase.id == knowledge_base_id)
    ).scalar_one_or_none()
    if exists is None:
        raise ResourceNotFoundError("知识库不存在")


def _document_sources(evidence: list[ChannelEvidence]) -> list[ChatSource]:
    """仅从 document 通道还原旧接口兼容的来源字段。"""
    sources: list[ChatSource] = []
    for item in evidence:
        if item.channel != "document":
            continue
        for hit in item.records:
            sources.append(
                ChatSource(
                    document_id=UUID(str(hit["doc_id"])),
                    document_name=str(hit["doc_name"]),
                    page_number=int(hit.get("page_number", 0)),
                    chunk_index=int(hit.get("chunk_index", 0)),
                    score=float(hit.get("rerank_score", hit.get("score", 0.0))),
                    text=str(hit["text"]),
                )
            )
    return sources
