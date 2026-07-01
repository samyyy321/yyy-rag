"""将可审阅的医疗图谱演示数据写入 Neo4j。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neo4j import Driver

from src.core.config import get_settings
from src.infra.neo4j_client import get_neo4j_driver


_ALLOWED_LABELS = {"Disease", "Symptom", "Drug", "Department", "Check", "Food"}
_ALLOWED_RELATIONSHIPS = {
    "HAS_SYMPTOM",
    "BELONGS_TO",
    "COMMON_DRUG",
    "RECOMMEND_DRUG",
    "NEED_CHECK",
    "DO_EAT",
    "NO_EAT",
    "ACOMPANY_WITH",
}


def load_graph_data(path: Path) -> dict[str, Any]:
    """读取并校验演示图谱 JSON 的顶层结构。"""
    graph_data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(graph_data, dict):
        raise ValueError("图谱演示数据必须是 JSON 对象")
    if not graph_data.get("disclaimer"):
        raise ValueError("图谱演示数据必须声明用途限制")
    return graph_data


def initialize_medical_graph(
    driver: Driver,
    graph_data: dict[str, object],
    *,
    database: str,
) -> None:
    """创建图谱约束并参数化 MERGE 演示节点关系；数据仅用于流程验证。"""
    nodes = _validate_nodes(graph_data.get("nodes"))
    relationships = _validate_relationships(graph_data.get("relationships"))

    with driver.session(database=database) as session:
        _create_constraints(session)
        session.execute_write(_merge_nodes, nodes)
        session.execute_write(_merge_relationships, relationships)


def _create_constraints(session: Any) -> None:
    """为各节点标签创建 name 唯一约束，允许脚本重复执行。"""
    for label in sorted(_ALLOWED_LABELS):
        constraint_name = f"{label.lower()}_name_unique"
        session.run(
            f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
            f"FOR (node:{label}) REQUIRE node.name IS UNIQUE"
        )


def _merge_nodes(tx: Any, nodes: list[dict[str, object]]) -> None:
    """通过参数化 name 和 properties 合并演示节点。"""
    for node in nodes:
        label = str(node["label"])
        tx.run(
            f"MERGE (node:{label} {{name: $name}}) "
            "SET node += $properties, node.demo_only = true",
            name=node["name"],
            properties=node["properties"],
        )


def _merge_relationships(tx: Any, relationships: list[dict[str, object]]) -> None:
    """通过参数化节点名称合并演示关系。"""
    for relationship in relationships:
        source = relationship["from"]
        target = relationship["to"]
        source_label = str(source["label"])
        target_label = str(target["label"])
        relationship_type = str(relationship["type"])
        tx.run(
            f"MATCH (source:{source_label} {{name: $source_name}}) "
            f"MATCH (target:{target_label} {{name: $target_name}}) "
            f"MERGE (source)-[relationship:{relationship_type}]->(target) "
            "SET relationship.demo_only = true",
            source_name=source["name"],
            target_name=target["name"],
        )


def _validate_nodes(raw_nodes: object) -> list[dict[str, object]]:
    """限制演示节点标签和属性，避免 JSON 数据改变 Cypher 结构。"""
    if not isinstance(raw_nodes, list):
        raise ValueError("nodes 必须是列表")

    nodes: list[dict[str, object]] = []
    for node in raw_nodes:
        if not isinstance(node, dict):
            raise ValueError("节点必须是对象")
        label = node.get("label")
        name = node.get("name")
        properties = node.get("properties", {})
        if label not in _ALLOWED_LABELS or not isinstance(name, str):
            raise ValueError("节点标签或名称不合法")
        if not isinstance(properties, dict):
            raise ValueError("节点 properties 必须是对象")
        nodes.append({"label": label, "name": name, "properties": properties})
    return nodes


def _validate_relationships(raw_relationships: object) -> list[dict[str, object]]:
    """限制演示关系类型和端点标签，避免 JSON 数据改变 Cypher 结构。"""
    if not isinstance(raw_relationships, list):
        raise ValueError("relationships 必须是列表")

    relationships: list[dict[str, object]] = []
    for relationship in raw_relationships:
        if not isinstance(relationship, dict):
            raise ValueError("关系必须是对象")
        source = relationship.get("from")
        target = relationship.get("to")
        relationship_type = relationship.get("type")
        if not isinstance(source, dict) or not isinstance(target, dict):
            raise ValueError("关系端点必须是对象")
        if relationship_type not in _ALLOWED_RELATIONSHIPS:
            raise ValueError("关系类型不合法")
        if source.get("label") not in _ALLOWED_LABELS or target.get("label") not in _ALLOWED_LABELS:
            raise ValueError("关系端点标签不合法")
        if not isinstance(source.get("name"), str) or not isinstance(target.get("name"), str):
            raise ValueError("关系端点名称不合法")
        relationships.append(
            {"from": source, "to": target, "type": relationship_type}
        )
    return relationships


def main() -> None:
    """在当前 Neo4j 配置中导入图谱演示数据。"""
    settings = get_settings()
    data_path = Path(__file__).parent / "data" / "medical_graph_demo.json"
    driver = get_neo4j_driver()
    try:
        initialize_medical_graph(
            driver,
            load_graph_data(data_path),
            database=settings.NEO4J_DATABASE,
        )
    finally:
        driver.close()
    print("医疗图谱演示数据初始化完成，仅用于验证流程，不能作为医疗依据。")


if __name__ == "__main__":
    main()
