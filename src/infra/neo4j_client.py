"""Neo4j 图谱查询客户端，仅向 GraphRAG 提供只读记录访问。"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from neo4j import GraphDatabase
from neo4j import Driver

from src.core.config import get_settings


@lru_cache
def get_neo4j_driver() -> Driver:
    """按配置延迟创建并缓存 Neo4j Driver。"""
    settings = get_settings()
    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )


def query_graph(cypher: str) -> list[dict[str, Any]]:
    """在配置的 Neo4j 数据库中执行已校验的只读 Cypher 并返回普通字典。"""
    settings = get_settings()
    driver = get_neo4j_driver()
    with driver.session(database=settings.NEO4J_DATABASE) as session:
        return session.execute_read(_run_query, cypher)


def _run_query(tx: Any, cypher: str) -> list[dict[str, Any]]:
    """在 Neo4j 只读事务中执行查询。"""
    return [record.data() for record in tx.run(cypher)]
