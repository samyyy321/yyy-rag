from unittest.mock import Mock

from src.api.main import app


def _route_paths(routes, prefix=""):
    """兼容不同 FastAPI 版本的嵌套路由结构并收集完整路径。"""
    paths = set()
    for route in routes:
        path = getattr(route, "path", None)
        if path is not None:
            paths.add(f"{prefix}{path}")
        if hasattr(route, "routes"):
            paths.update(_route_paths(route.routes, prefix))
        if hasattr(route, "original_router"):
            # 新版 FastAPI 将 include_router 前缀保存在 include_context 中。
            included_prefix = route.include_context.prefix
            paths.update(_route_paths(route.original_router.routes, f"{prefix}{included_prefix}"))
    return paths


def test_api_exposes_required_paths():
    paths = _route_paths(app.routes)
    assert "/api/v1/knowledge-bases" in paths
    assert "/api/v1/knowledge-bases/{knowledge_base_id}/documents" in paths
    assert "/api/v1/documents/{document_id}" in paths
    assert "/api/v1/chat" in paths
    assert "/api/v1/chat/stream" in paths
    assert "/api/v1/health" in paths

def test_document_dependencies_load_only_when_document_channel_is_selected(monkeypatch):
    """图谱和 SQL-only 请求不应创建 Milvus 或 Embedding 客户端。"""
    from src.api.routes import chat as chat_routes

    embedding = object()
    milvus = object()
    get_embedding = Mock(return_value=embedding)
    get_milvus = Mock(return_value=milvus)
    monkeypatch.setattr(chat_routes, "get_embedding", get_embedding)
    monkeypatch.setattr(chat_routes, "get_milvus", get_milvus)

    assert chat_routes._get_document_dependencies(["graph", "sql"]) == (None, None)
    get_embedding.assert_not_called()
    get_milvus.assert_not_called()

    assert chat_routes._get_document_dependencies(["document", "graph"]) == (
        embedding,
        milvus,
    )
    get_embedding.assert_called_once()
    get_milvus.assert_called_once()
