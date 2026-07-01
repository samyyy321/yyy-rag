"""NL2SQL 和 NL2Cypher 的最小只读安全校验。"""

from __future__ import annotations

import re


class QuerySafetyError(ValueError):
    """模型生成的查询不符合只读白名单约束时抛出。"""


_ALLOWED_SQL_TABLES = {
    "categories",
    "products",
    "customers",
    "orders",
    "order_items",
}
_SQL_FORBIDDEN_WORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "grant",
    "revoke",
    "truncate",
    "copy",
    "execute",
}
_CYPHER_FORBIDDEN_WORDS = {
    "create",
    "merge",
    "delete",
    "detach",
    "set",
    "remove",
    "call",
    "load csv",
    "foreach",
}


def validate_sql(sql: str) -> str:
    """校验并规范化只读取演示运营表的单条 SELECT 查询。"""
    statement = _clean_statement(sql)
    _reject_forbidden_words(statement, _SQL_FORBIDDEN_WORDS)

    if not re.match(r"^select\b", statement, flags=re.IGNORECASE):
        raise QuerySafetyError("只允许 SELECT 查询")

    for table_name in _extract_sql_tables(statement):
        if table_name not in _ALLOWED_SQL_TABLES:
            raise QuerySafetyError(f"不允许查询表: {table_name}")

    return _apply_limit(statement, maximum=100)


def validate_cypher(cypher: str) -> str:
    """校验并规范化只读单条 MATCH/OPTIONAL MATCH 图谱查询。"""
    statement = _clean_statement(cypher)
    _reject_forbidden_words(statement, _CYPHER_FORBIDDEN_WORDS)

    if not re.match(r"^(optional\s+match|match)\b", statement, flags=re.IGNORECASE):
        raise QuerySafetyError("只允许 MATCH 或 OPTIONAL MATCH 查询")
    if not re.search(r"\breturn\b", statement, flags=re.IGNORECASE):
        raise QuerySafetyError("Cypher 查询必须包含 RETURN")

    return _apply_limit(statement, maximum=20)


def _clean_statement(query: str) -> str:
    """移除代码围栏和末尾分号，并拒绝注释及多语句输入。"""
    statement = query.strip()
    if statement.startswith("```") and statement.endswith("```"):
        statement = statement.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    if not statement:
        raise QuerySafetyError("查询不能为空")
    if "--" in statement or "/*" in statement or "*/" in statement:
        raise QuerySafetyError("不允许查询注释")

    statement = statement.rstrip(";").strip()
    if not statement or ";" in statement:
        raise QuerySafetyError("只允许单条查询")
    return statement


def _reject_forbidden_words(statement: str, forbidden_words: set[str]) -> None:
    """拒绝出现在查询任意位置的写入或管理关键字。"""
    for word in forbidden_words:
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, statement, flags=re.IGNORECASE):
            raise QuerySafetyError(f"不允许的关键字: {word}")


def _extract_sql_tables(statement: str) -> set[str]:
    """提取 FROM/JOIN 后的简单表名，用于运营表白名单校验。"""
    matches = re.findall(
        r"\b(?:from|join)\s+\"?([a-z_][a-z0-9_]*)\"?",
        statement,
        flags=re.IGNORECASE,
    )
    return {table_name.lower() for table_name in matches}


def _apply_limit(statement: str, *, maximum: int) -> str:
    """为查询补齐 LIMIT，并拒绝超过指定上限的显式 LIMIT。"""
    limit_match = re.search(r"\blimit\s+(\d+)\b", statement, flags=re.IGNORECASE)
    if limit_match is None:
        return f"{statement} LIMIT {maximum}"

    if int(limit_match.group(1)) > maximum:
        raise QuerySafetyError(f"LIMIT 不能大于 {maximum}")
    return statement
