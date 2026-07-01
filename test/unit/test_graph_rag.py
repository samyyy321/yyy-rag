from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_graph_retries_once_after_query_failure(monkeypatch):
    """首次图谱查询失败时，应重新生成查询并在第二次成功返回证据。"""
    from src.query import graph_rag

    monkeypatch.setattr(
        graph_rag,
        "extract_entities",
        AsyncMock(return_value={"diseases": ["高血压"]}),
    )
    generate_cypher = AsyncMock(side_effect=["MATCH (d:Disease) RETURN d", "MATCH (d:Disease) RETURN d"])
    monkeypatch.setattr(graph_rag, "generate_cypher", generate_cypher)

    results = [RuntimeError("Neo4j unavailable"), [{"name": "高血压"}]]

    def query_graph(_cypher):
        result = results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(graph_rag, "query_graph", query_graph)

    evidence = await graph_rag.retrieve_graph_evidence("高血压有什么症状", object())

    assert evidence is not None
    assert evidence.channel == "graph"
    assert "高血压" in evidence.content
    assert generate_cypher.await_count == 2
