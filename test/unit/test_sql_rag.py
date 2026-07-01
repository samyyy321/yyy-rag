from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_sql_retries_once_after_query_failure(monkeypatch):
    """首次 SQL 执行失败时，应重新生成查询并在第二次成功返回证据。"""
    from src.query import sql_rag

    generate_sql = AsyncMock(
        side_effect=[
            "SELECT name, price FROM products",
            "SELECT name, price FROM products",
        ]
    )
    monkeypatch.setattr(sql_rag, "generate_sql", generate_sql)

    results = [RuntimeError("PostgreSQL unavailable"), [{"name": "演示商品", "price": 99}]]

    def query_operational_data(_sql):
        result = results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(sql_rag, "query_operational_data", query_operational_data)

    evidence = await sql_rag.retrieve_sql_evidence("商品价格是多少", object())

    assert evidence is not None
    assert evidence.channel == "sql"
    assert "演示商品" in evidence.content
    assert generate_sql.await_count == 2
