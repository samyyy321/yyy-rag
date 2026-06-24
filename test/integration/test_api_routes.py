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
