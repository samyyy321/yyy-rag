import pytest

from src.query.query_safety import QuerySafetyError, validate_cypher, validate_sql


def test_validate_sql_adds_default_limit_to_allowed_select():
    """合法的演示运营表 SELECT 缺少 LIMIT 时应自动补齐。"""
    assert validate_sql("SELECT name, price FROM products") == (
        "SELECT name, price FROM products LIMIT 100"
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM products LIMIT 101",
        "SELECT * FROM products; DELETE FROM products",
        "UPDATE products SET stock = 0",
        "SELECT * FROM knowledge_bases",
    ],
)
def test_validate_sql_rejects_unsafe_or_out_of_scope_queries(sql):
    """SQL 只能读取白名单演示表，且 LIMIT 不得超过上限。"""
    with pytest.raises(QuerySafetyError):
        validate_sql(sql)


def test_validate_cypher_adds_default_limit_to_read_query():
    """合法图谱 MATCH 缺少 LIMIT 时应自动补齐。"""
    assert validate_cypher("MATCH (d:Disease) RETURN d.name") == (
        "MATCH (d:Disease) RETURN d.name LIMIT 20"
    )


@pytest.mark.parametrize(
    "cypher",
    [
        "MATCH (d:Disease) RETURN d LIMIT 21",
        "CREATE (:Disease {name: '演示'})",
        "MATCH (d:Disease) DELETE d",
        "CALL db.labels()",
        "LOAD CSV FROM 'file:///data.csv' AS row RETURN row",
    ],
)
def test_validate_cypher_rejects_non_read_or_excessive_queries(cypher):
    """Cypher 只能执行受限的只读 MATCH 查询。"""
    with pytest.raises(QuerySafetyError):
        validate_cypher(cypher)
