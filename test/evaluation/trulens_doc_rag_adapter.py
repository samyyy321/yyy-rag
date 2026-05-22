"""独立于生产链路的 TruLens 文档 RAG 评估适配器。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from langchain_core.messages import SystemMessage
from langchain_core.prompts import PromptTemplate
from trulens.apps.app import instrument

from src.query.doc_rag import format_doc_context, search_docs_raw
from src.query.prompts import DOC_QA_PROMPT


@dataclass(frozen=True)
class EvaluationCase:
    """一条可重复执行的离线 RAG 评测问题。"""

    id: str
    question: str
    expected_answer: str | None = None


@dataclass(frozen=True)
class RagEvaluationRecord:
    """一次 RAG 调用中实际使用的输入、上下文和输出。"""

    question: str
    contexts: list[str]
    answer: str


SearchFunction = Callable[..., Awaitable[list[dict[str, Any]]]]


def load_evaluation_cases(file_path: str | Path) -> list[EvaluationCase]:
    """读取并校验 JSONL 评测集，避免错误样本污染评分统计。"""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"评测集文件不存在: {path}")

    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            item = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"第 {line_number} 行不是合法 JSON") from exc

        case_id = item.get("id") if isinstance(item, dict) else None
        question = item.get("question") if isinstance(item, dict) else None
        expected_answer = item.get("expected_answer") if isinstance(item, dict) else None
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"第 {line_number} 行缺少非空 id")
        if case_id in seen_ids:
            raise ValueError(f"评测集存在重复 id: {case_id}")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"第 {line_number} 行缺少非空 question")
        if expected_answer is not None and not isinstance(expected_answer, str):
            raise ValueError(f"第 {line_number} 行的 expected_answer 必须是字符串")

        seen_ids.add(case_id)
        cases.append(
            EvaluationCase(
                id=case_id,
                question=question,
                expected_answer=expected_answer,
            )
        )

    if not cases:
        raise ValueError("评测集不能为空")
    return cases


class DocRagEvaluationAdapter:
    """复用当前 RAG 能力的评估外层，生产模块不依赖 TruLens。"""

    def __init__(
        self,
        *,
        embedding_model: Any,
        milvus_client: Any,
        llm: Any,
        search_function: SearchFunction = search_docs_raw,
        context_formatter: Callable[[list[dict[str, Any]]], str] = format_doc_context,
        prompt_template: str = DOC_QA_PROMPT,
        top_k: int = 20,
        rerank_top_k: int = 5,
        role: str = "patient",
        use_hyde: bool = True,
    ) -> None:
        """注入既有基础设施，使该适配器可在单测中完全替换外部依赖。"""
        self.embedding_model = embedding_model
        self.milvus_client = milvus_client
        self.llm = llm
        self.search_function = search_function
        self.context_formatter = context_formatter
        self.prompt_template = prompt_template
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k
        self.role = role
        self.use_hyde = use_hyde

    @instrument
    async def retrieve(self, question: str) -> list[dict[str, Any]]:
        """执行当前生产链路使用的粗检索、重排和 HyDE 配置。"""
        return await self.search_function(
            question=question,
            embedding_model=self.embedding_model,
            milvus_client=self.milvus_client,
            top_k=self.top_k,
            rerank_top_k=self.rerank_top_k,
            llm=self.llm,
            use_hyde=self.use_hyde,
        )

    @instrument
    def extract_context_texts(self, hits: list[dict[str, Any]]) -> list[str]:
        """提取每个命中的原始文本，供逐片段相关性评估使用。"""
        return [text for hit in hits if isinstance((text := hit.get("text")), str) and text]

    @instrument
    def format_context(self, hits: list[dict[str, Any]]) -> str:
        """复用生产上下文格式，确保回答与评估的证据完全一致。"""
        return self.context_formatter(hits)

    @instrument
    async def generate_answer(self, question: str, context: str) -> str:
        """使用生产提示词和回答模型生成待评估答案。"""
        prompt = self.prompt_template.format(
            question=question,
            context=context,
            role=self.role,
        )
        response = await self.llm.ainvoke([SystemMessage(content=prompt)])
        return response.content if isinstance(response.content, str) else str(response.content)

    @instrument
    async def run(self, question: str) -> RagEvaluationRecord:
        """执行一次完整评估调用，并返回 TruLens 可追踪的真实证据。"""
        # 1. 复用生产检索链路，获得实际参与 RAG 回答的重排后文档片段。
        hits = await self.retrieve(question)

        # 2. 保留每个片段的原始文本，供 Context Relevance 等指标逐片段评分。
        contexts = self.extract_context_texts(hits)

        # 3. 使用与生产回答一致的格式拼接上下文，避免评测证据与实际回答不一致。
        context = self.format_context(hits)

        # 4. 基于问题和真实上下文生成回答，供 Answer Relevance 与 Groundedness 评估。
        answer = await self.generate_answer(question, context)

        # 5. 返回结构化证据；TruLens 会记录问题、上下文和回答的完整调用链。
        return RagEvaluationRecord(question=question, contexts=contexts, answer=answer)


