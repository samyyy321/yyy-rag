"""Chat RAG 问答与流式问答路由。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import cast

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from pymilvus import MilvusClient
from sqlalchemy.orm import Session

from src.api.dependencies import (
    get_chat_model,
    get_database,
    get_embedding,
    get_milvus,
)
from src.api.schemas import ChatRequest, ChatResponse
from src.services.chat_service import answer_question, stream_answer

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_database),
    llm: BaseChatModel = Depends(get_chat_model),
) -> ChatResponse:
    """按请求通道执行非流式问答，仅 document 通道加载文档基础依赖。"""
    embedding_model, milvus_client = _get_document_dependencies(payload.channels)
    return await answer_question(
        knowledge_base_id=payload.knowledge_base_id,
        question=payload.question,
        role=payload.role,
        top_k=payload.top_k,
        rerank_top_k=payload.rerank_top_k,
        use_hyde=payload.use_hyde,
        channels=payload.channels,
        db=db,
        embedding_model=embedding_model,
        milvus_client=milvus_client,
        llm=llm,
    )


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_database),
    llm: BaseChatModel = Depends(get_chat_model),
) -> StreamingResponse:
    """以 Server-Sent Events 流式返回指定通道的 RAG 回答。"""
    embedding_model, milvus_client = _get_document_dependencies(payload.channels)

    async def event_stream() -> AsyncIterator[str]:
        async for content in stream_answer(
            knowledge_base_id=payload.knowledge_base_id,
            question=payload.question,
            role=payload.role,
            top_k=payload.top_k,
            rerank_top_k=payload.rerank_top_k,
            use_hyde=payload.use_hyde,
            channels=payload.channels,
            db=db,
            embedding_model=embedding_model,
            milvus_client=milvus_client,
            llm=llm,
        ):
            # 每个 SSE 事件只承载一个模型文本片段，便于前端按到达顺序拼接。
            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


def _get_document_dependencies(
    channels: list[str],
) -> tuple[Embeddings | None, MilvusClient | None]:
    """仅在 document 通道被选择时创建 Embedding 与 Milvus 客户端。"""
    if "document" not in channels:
        return None, None
    return cast(Embeddings, get_embedding()), cast(MilvusClient, get_milvus())
