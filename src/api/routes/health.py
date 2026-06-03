"""应用依赖健康检查路由。"""

from fastapi import APIRouter, Depends, HTTPException, status
from pymilvus import MilvusClient
from sqlalchemy.orm import Session

from src.api.dependencies import get_database, get_milvus, get_storage
from src.api.schemas import HealthResponse
from src.infra.minio_client import ObjectStorage
from src.services.chat_service import check_health

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(
    db: Session = Depends(get_database),
    storage: ObjectStorage = Depends(get_storage),
    milvus_client: MilvusClient = Depends(get_milvus),
) -> HealthResponse:
    """返回 API 及其基础依赖的健康状态。"""
    if not check_health(db, storage, milvus_client):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务依赖不可用",
        )
    return HealthResponse(status="ok")
