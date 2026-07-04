"""单通道检索与 asyncio.gather 多通道融合编排。"""

from __future__ import annotations

import asyncio
from uuid import UUID

from loguru import logger
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from pymilvus import MilvusClient
from sqlalchemy.orm import Session

from src.query.channel_types import ChannelEvidence
from src.query.doc_rag import format_doc_context, search_docs_raw
from src.query.graph_rag import retrieve_graph_evidence
from src.query.prompts import (
    DOC_QA_PROMPT,
    FUSION_PROMPT,
    GRAPH_QA_PROMPT,
    SQL_QA_PROMPT,
)
from src.query.sql_rag import retrieve_sql_evidence


async def retrieve_document_evidence(
    *,
    knowledge_base_id: UUID | None,
    question: str,
    top_k: int,
    rerank_top_k: int,
    use_hyde: bool,
    embedding_model: Embeddings | None,
    milvus_client: MilvusClient | None,
    llm: BaseChatModel,
) -> ChannelEvidence | None:
    """复用现有 Milvus 文档检索，转为文档通道证据。"""
    if knowledge_base_id is None:
        raise ValueError("document 通道需要知识库 ID")
    if embedding_model is None or milvus_client is None:
        raise ValueError("document 通道需要 Milvus 和 Embedding 依赖")
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
        return None
    return ChannelEvidence(
        channel="document",
        content=format_doc_context(hits),
        records=tuple(hits),
    )


async def collect_evidence(
    channels: list[str],
    *,
    knowledge_base_id: UUID | None,
    question: str,
    top_k: int,
    rerank_top_k: int,
    use_hyde: bool,
    db: Session,
    embedding_model: Embeddings | None,
    milvus_client: MilvusClient | None,
    llm: BaseChatModel,
) -> list[ChannelEvidence]:
    """按请求指定的通道收集证据；多通道时并行且容忍单通道失败。"""
    if len(channels) == 1:
        evidence = await _retrieve_channel(
            channels[0],
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
        return [evidence] if evidence is not None else []

    results = await asyncio.gather(
        *(
            _retrieve_channel(
                channel,
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
            for channel in channels
        ),
        return_exceptions=True,
    )
    evidence_list: list[ChannelEvidence] = []
    for channel, result in zip(channels, results, strict=True):
        if isinstance(result, Exception):
            logger.warning(f"{channel} 通道未返回证据: {result}")
            continue
        if result is not None:
            evidence_list.append(result)
    return evidence_list


async def generate_channel_answer(
    *,
    question: str,
    role: str,
    evidence: list[ChannelEvidence],
    llm: BaseChatModel,
) -> str:
    """根据单通道或多通道证据选择提示词并生成完整回答。"""
    prompt = build_answer_prompt(question=question, role=role, evidence=evidence)
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    return response.content if isinstance(response.content, str) else str(response.content)


def build_answer_prompt(
    *,
    question: str,
    role: str,
    evidence: list[ChannelEvidence],
) -> str:
    """为单通道或多通道证据构建回答提示词。"""
    if len(evidence) > 1:
        return FUSION_PROMPT.format(
            question=question,
            role=role,
            sources=_format_fusion_sources(evidence),
        )

    item = evidence[0]
    if item.channel == "document":
        return DOC_QA_PROMPT.format(question=question, context=item.content, role=role)
    if item.channel == "graph":
        return GRAPH_QA_PROMPT.format(
            question=question,
            graph_result=item.content,
            role=role,
        )
    return SQL_QA_PROMPT.format(
        question=question,
        sql="已执行受限只读运营数据查询",
        result=item.content,
    )


async def _retrieve_channel(
    channel: str,
    *,
    knowledge_base_id: UUID | None,
    question: str,
    top_k: int,
    rerank_top_k: int,
    use_hyde: bool,
    db: Session,
    embedding_model: Embeddings | None,
    milvus_client: MilvusClient | None,
    llm: BaseChatModel,
) -> ChannelEvidence | None:
    """分发到一个已由请求模型校验过的检索通道。"""
    if channel == "document":
        return await retrieve_document_evidence(
            knowledge_base_id=knowledge_base_id,
            question=question,
            top_k=top_k,
            rerank_top_k=rerank_top_k,
            use_hyde=use_hyde,
            embedding_model=embedding_model,
            milvus_client=milvus_client,
            llm=llm,
        )
    if channel == "graph":
        return await retrieve_graph_evidence(question, llm)
    if channel == "sql":
        return await retrieve_sql_evidence(question, llm)
    raise ValueError(f"不支持的检索通道: {channel}")


def _format_fusion_sources(evidence: list[ChannelEvidence]) -> str:
    """为融合提示词标注不同证据通道，避免模型混淆来源。"""
    names = {
        "document": "文档知识库",
        "graph": "医学知识图谱",
        "sql": "运营数据库",
    }
    return "\n\n".join(
        f"【{names[item.channel]}】\n{item.content}" for item in evidence
    )
