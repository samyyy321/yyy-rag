"""Chat RAG 问答路由。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from pymilvus import MilvusClient
from sqlalchemy.orm import Session

from src.api.dependencies import get_chat_model, get_database, get_embedding, get_milvus
from src.api.schemas import ChatRequest, ChatResponse
from src.services.chat_service import answer_question

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_database),
    embedding_model: Embeddings = Depends(get_embedding),
    milvus_client: MilvusClient = Depends(get_milvus),
    llm: BaseChatModel = Depends(get_chat_model),
) -> ChatResponse:
    """在指定知识库范围内执行 RAG 问答。"""
    return await answer_question(
        knowledge_base_id=payload.knowledge_base_id,
        question=payload.question,
        role=payload.role,
        top_k=payload.top_k,
        rerank_top_k=payload.rerank_top_k,
        use_hyde=payload.use_hyde,
        db=db,
        embedding_model=embedding_model,
        milvus_client=milvus_client,
        llm=llm,
    )
