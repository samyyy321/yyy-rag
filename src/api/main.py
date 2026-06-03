"""FastAPI 应用入口和统一业务异常映射。"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.routes import chat, documents, health, knowledge_bases
from src.services.errors import ExternalStorageError, ResourceConflictError, ResourceNotFoundError


app = FastAPI(title="RAG 文档知识库后端")


@app.exception_handler(ResourceNotFoundError)
async def handle_not_found(_: Request, exc: ResourceNotFoundError) -> JSONResponse:
    """把业务资源不存在转换为 HTTP 404。"""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ResourceConflictError)
async def handle_conflict(_: Request, exc: ResourceConflictError) -> JSONResponse:
    """把业务状态冲突转换为 HTTP 409。"""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ExternalStorageError)
async def handle_external_storage(_: Request, exc: ExternalStorageError) -> JSONResponse:
    """把外部存储清理失败转换为不泄露堆栈的 HTTP 500。"""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.include_router(knowledge_bases.router, prefix="/api/v1")
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(health.router)
