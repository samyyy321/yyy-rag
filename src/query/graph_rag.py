"""GraphRAG 实体抽取、Cypher 生成和图谱证据检索。"""

from __future__ import annotations

import asyncio
import json

from loguru import logger
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage

from src.infra.neo4j_client import query_graph
from src.query.channel_types import ChannelEvidence
from src.query.prompts import ENTITY_EXTRACT_PROMPT, NL2CYPHER_PROMPT
from src.query.query_safety import validate_cypher


async def retrieve_graph_evidence(
    question: str,
    llm: BaseChatModel,
) -> ChannelEvidence | None:
    """检索图谱证据；任一步失败时最多重新执行一次完整链路。"""
    for attempt in range(2):
        try:
            entities = await extract_entities(question, llm)
            cypher = await generate_cypher(question, entities, llm)
            rows = await asyncio.to_thread(query_graph, validate_cypher(cypher))
            if not rows:
                return None
            content = json.dumps(rows, ensure_ascii=False, default=str)
            return ChannelEvidence(channel="graph", content=f"医学知识图谱：\n{content}")
        except Exception as exc:
            logger.warning(f"GraphRAG 第 {attempt + 1} 次执行失败: {exc}")
    return None


async def extract_entities(question: str, llm: BaseChatModel) -> dict[str, object]:
    """用预置提示词抽取问题中的图谱实体。"""
    response_text = await _invoke_prompt(
        llm,
        ENTITY_EXTRACT_PROMPT.format(question=question),
    )
    payload = _parse_json(response_text)
    if not isinstance(payload, dict):
        raise ValueError("实体抽取结果必须是 JSON 对象")
    return payload


async def generate_cypher(
    question: str,
    entities: dict[str, object],
    llm: BaseChatModel,
) -> str:
    """用预置提示词生成 Neo4j Cypher 查询。"""
    return await _invoke_prompt(
        llm,
        NL2CYPHER_PROMPT.format(
            question=question,
            entities=json.dumps(entities, ensure_ascii=False),
        ),
    )


async def _invoke_prompt(llm: BaseChatModel, prompt: str) -> str:
    """调用聊天模型并提取单一文本响应。"""
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    return response.content if isinstance(response.content, str) else str(response.content)


def _parse_json(text: str) -> object:
    """解析模型可能带 Markdown 围栏的 JSON 文本。"""
    value = text.strip()
    if value.startswith("```") and value.endswith("```"):
        value = value.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(value)
