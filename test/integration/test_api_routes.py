from src.api.main import app


def _route_paths(routes):
    paths = set()
    for route in routes:
        if hasattr(route, "path"):
            paths.add(route.path)
        if hasattr(route, "routes"):
            paths.update(_route_paths(route.routes))
    return paths


def test_api_exposes_required_paths():
    paths = _route_paths(app.routes)
    assert "/api/v1/knowledge-bases" in paths
    assert "/api/v1/knowledge-bases/{knowledge_base_id}/documents" in paths
    assert "/api/v1/documents/{document_id}" in paths
    assert "/api/v1/chat" in paths
    assert "/api/v1/health" in paths
