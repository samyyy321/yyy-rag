"""NL2SQL 生成、只读查询和运营数据证据检索。"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from loguru import logger
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from sqlalchemy import text

from src.db.database import engine
from src.query.channel_types import ChannelEvidence
from src.query.prompts import NL2SQL_PROMPT
from src.query.query_safety import validate_sql


async def retrieve_sql_evidence(
    question: str,
    llm: BaseChatModel,
) -> ChannelEvidence | None:
    """检索运营数据库证据；任一步失败时最多重新执行一次完整链路。"""
    for attempt in range(2):
        try:
            sql = await generate_sql(question, llm)
            safe_sql = validate_sql(sql)
            rows = await asyncio.to_thread(query_operational_data, safe_sql)
            if not rows:
                return None
            result = json.dumps(rows, ensure_ascii=False, default=str)
            content = f"运营数据库：\n执行 SQL：{safe_sql}\n查询结果：{result}"
            return ChannelEvidence(channel="sql", content=content, records=tuple(rows))
        except Exception as exc:
            logger.warning(f"NL2SQL 第 {attempt + 1} 次执行失败: {exc}")
    return None


async def generate_sql(question: str, llm: BaseChatModel) -> str:
    """用预置提示词生成 PostgreSQL SELECT 查询。"""
    response = await llm.ainvoke(
        [SystemMessage(content=NL2SQL_PROMPT.format(question=question))]
    )
    return response.content if isinstance(response.content, str) else str(response.content)


def query_operational_data(sql: str) -> list[dict[str, Any]]:
    """执行已校验的运营数据只读 SQL，并转为普通字典列表。"""
    with engine.connect() as connection:
        result = connection.execute(text(sql))
        return [dict(row) for row in result.mappings()]
