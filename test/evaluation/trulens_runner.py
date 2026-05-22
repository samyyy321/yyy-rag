"""TruLens 指标与记录器构造工具。"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import PrivateAttr
from trulens.apps.app import TruApp
from trulens.core import Metric, Provider, TruSession

from src.core.config import get_settings
from test.evaluation.trulens_doc_rag_adapter import (
    DocRagEvaluationAdapter,
    EvaluationCase,
    RagEvaluationRecord,
)


EVALUATION_APP_NAME = "yyy-rag-doc-rag-evaluation"
EVALUATION_APP_VERSION = "v1"


def serialize_evaluation_record(record: RagEvaluationRecord | Mapping[str, Any]) -> str:
    """将评测证据编码为 OTel 主输出，使三项指标获得相同的上下文和答案。"""
    if isinstance(record, RagEvaluationRecord):
        payload = {"contexts": record.contexts, "answer": record.answer}
    else:
        payload = {
            "contexts": record.get("contexts", []),
            "answer": record.get("answer", ""),
        }
    return json.dumps(payload, ensure_ascii=False)


class DocRagTruApp(TruApp):
    """为当前结构化评测结果定义明确的 TruLens 主输出序列化规则。"""

    def main_output(self, func: Any, sig: Any, bindings: Any, ret: Any) -> str:
        """避免 TruLens 默认提取 dataclass 的第一个字段 question 作为输出。"""
        if isinstance(ret, RagEvaluationRecord) or isinstance(ret, Mapping):
            return serialize_evaluation_record(ret)
        return super().main_output(func, sig, bindings, ret)


def create_trulens_session(
    *,
    environ: Mapping[str, str] | None = None,
    session_factory: Callable[..., TruSession] = TruSession,
) -> TruSession:
    """按配置连接 PostgreSQL，未配置时保留 TruLens 默认 SQLite 回退。"""
    values = os.environ if environ is None else environ
    database_url = values.get("TRULENS_DATABASE_URL", "").strip()
    return session_factory(database_url=database_url) if database_url else session_factory()


def get_evaluation_llm() -> ChatOpenAI:
    """创建独立裁判模型，避免评估配置改变生产回答模型。"""
    settings = get_settings()
    model = os.getenv("TRULENS_EVAL_MODEL", settings.LLM_MODEL)
    if not settings.API_KEY:
        raise RuntimeError("缺少 API_KEY，无法运行 TruLens 远程评估")

    return ChatOpenAI(
        model=model,
        api_key=settings.API_KEY,
        base_url=settings.BASE_URL,
        temperature=0,
        timeout=90,
        max_retries=1,
    )


class RagTriadJudge(Provider):
    """使用严格 JSON 协议执行 RAG Triad，避免自由文本评分越界。"""

    _llm_factory: Callable[[], Any] = PrivateAttr(default_factory=lambda: (lambda: get_evaluation_llm()))

    def __init__(
        self,
        *,
        llm_factory: Callable[[], Any] = get_evaluation_llm,
        **kwargs: Any,
    ) -> None:
        """保留可注入模型工厂，单元测试无需调用远程 DashScope。"""
        super().__init__(**kwargs)
        self._llm_factory = llm_factory

    @staticmethod
    def _record_values(
        record: RagEvaluationRecord | Mapping[str, Any] | str,
    ) -> tuple[list[str], str]:
        """兼容运行时对象、持久化字典及 OTel 主输出 JSON 字符串。"""
        if isinstance(record, RagEvaluationRecord):
            return record.contexts, record.answer
        if isinstance(record, str):
            try:
                record = json.loads(record)
            except json.JSONDecodeError as exc:
                raise ValueError("TruLens 主输出不是合法的评测记录 JSON") from exc

        contexts = record.get("contexts", [])
        answer = record.get("answer", "")
        if not isinstance(contexts, list) or not all(
            isinstance(item, str) for item in contexts
        ):
            raise ValueError("TruLens 评估记录缺少字符串 contexts")
        if not isinstance(answer, str):
            raise ValueError("TruLens 评估记录缺少字符串 answer")
        return contexts, answer

    @staticmethod
    def _parse_strict_score(raw_output: str) -> tuple[int, str]:
        """解析裁判 JSON，并拒绝 0 到 3 之外的评分。"""
        content = raw_output.strip()
        if content.startswith("```") and content.endswith("```"):
            content = "\n".join(
                line for line in content.splitlines() if not line.strip().startswith("```")
            ).strip()

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("裁判模型未返回合法 JSON") from exc

        if not isinstance(payload, dict):
            raise ValueError("裁判模型 JSON 顶层必须是对象")
        score = payload.get("score")
        reason = payload.get("reason")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("裁判模型 JSON 缺少数值 score")
        if int(score) != score or not 0 <= int(score) <= 3:
            raise ValueError("裁判模型 score 必须是 0 到 3 的整数")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("裁判模型 JSON 缺少非空 reason")
        return int(score), reason.strip()

    def _score_with_retry(self, *, task: str, evidence: str) -> tuple[float, dict[str, str]]:
        """调用裁判模型并在格式或范围非法时仅重试一次。"""
        system_prompt = """你是严格的 RAG 评测裁判。
只能输出一个合法 JSON 对象，禁止 Markdown、代码块或额外文本：
{"score": 0, "reason": "简短中文理由"}
score 必须是 0、1、2、3 中的整数：0 最差，3 最好。
不得输出 4、5、10、百分比、小数或其他字段。"""
        user_prompt = f"评测任务：{task}\n\n评测证据：\n{evidence}"
        last_error: ValueError | None = None
        last_output = ""

        for attempt in range(2):
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            if attempt == 1:
                messages.append(
                    HumanMessage(
                        content=(
                            "你上一次输出不符合协议："
                            f"{last_output}\n请只重新输出合法 JSON，score 必须为 0、1、2 或 3。"
                        )
                    )
                )

            response = self._llm_factory().invoke(messages)
            content = response.content if isinstance(response.content, str) else str(response.content)
            last_output = content
            try:
                score, reason = self._parse_strict_score(content)
                return score / 3.0, {"reason": reason, "raw_score": str(score)}
            except ValueError as exc:
                last_error = exc

        raise ValueError(
            f"裁判模型两次均未返回合法 0 到 3 JSON 评分：{last_error}"
        )

    def context_relevance(
        self,
        question: str,
        record: RagEvaluationRecord | Mapping[str, Any] | str,
    ) -> tuple[float, dict[str, Any]]:
        """逐片段评估上下文与问题的相关性，返回归一化平均分。"""
        contexts, _ = self._record_values(record)
        if not contexts:
            return 0.0, {"reason": "没有检索上下文", "context_reasons": []}

        scores: list[float] = []
        reasons: list[dict[str, str]] = []
        for context in contexts:
            score, reason = self._score_with_retry(
                task="判断 CONTEXT 与 QUESTION 的相关性。",
                evidence=f"QUESTION:\n{question}\n\nCONTEXT:\n{context}",
            )
            scores.append(score)
            reasons.append(reason)
        return float(np.mean(scores)), {"context_reasons": reasons}

    def answer_relevance(
        self,
        question: str,
        record: RagEvaluationRecord | Mapping[str, Any] | str,
    ) -> tuple[float, dict[str, str]]:
        """评估 ANSWER 是否直接回答 QUESTION，不评估其事实正确性。"""
        _, answer = self._record_values(record)
        return self._score_with_retry(
            task="判断 ANSWER 是否直接、完整地回应 QUESTION。",
            evidence=f"QUESTION:\n{question}\n\nANSWER:\n{answer}",
        )

    def groundedness(
        self,
        question: str,
        record: RagEvaluationRecord | Mapping[str, Any] | str,
    ) -> tuple[float, dict[str, str]]:
        """评估 ANSWER 中的陈述是否由 CONTEXT 支撑。"""
        del question
        contexts, answer = self._record_values(record)
        return self._score_with_retry(
            task="判断 ANSWER 是否完全由 CONTEXT 支撑；不要依据外部知识评分。",
            evidence=f"CONTEXT:\n{'\n\n'.join(contexts)}\n\nANSWER:\n{answer}",
        )


def build_trulens_feedbacks(judge_llm: ChatOpenAI) -> list[Metric]:
    """构造使用严格 JSON 评分协议的三项 RAG 指标。"""
    judge = RagTriadJudge(llm_factory=lambda: judge_llm)
    return [
        Metric(implementation=judge.context_relevance, name="Context Relevance").on_input_output(),
        Metric(implementation=judge.answer_relevance, name="Answer Relevance").on_input_output(),
        Metric(implementation=judge.groundedness, name="Groundedness").on_input_output(),
    ]


def create_trulens_recorder(
    adapter: DocRagEvaluationAdapter,
    judge_llm: ChatOpenAI,
    session: TruSession | None = None,
) -> TruApp:
    """创建本地记录器；仅由集成评测调用，不进入生产请求路径。"""
    return DocRagTruApp(
        adapter,
        app_name=EVALUATION_APP_NAME,
        app_version=EVALUATION_APP_VERSION,
        feedbacks=build_trulens_feedbacks(judge_llm),
        session=session or create_trulens_session(),
        start_evaluator=False,
    )


async def run_evaluation_case(
    recorder: TruApp,
    adapter: DocRagEvaluationAdapter,
    case: EvaluationCase,
) -> RagEvaluationRecord:
    """在 OTel 记录上下文中执行一条样本，并等待追踪记录落库。"""
    with recorder as recording:
        result = await adapter.run(case.question)

    # OTel 会异步写入事件和聚合记录；等待追踪落库，不在 pytest 中无限等待异步评分。
    recording.get()
    return result




async def run_evaluation_case_with_feedback(
    recorder: TruApp,
    adapter: DocRagEvaluationAdapter,
    case: EvaluationCase,
    *,
    feedback_timeout: float = 180,
) -> tuple[RagEvaluationRecord, Any]:
    """执行一条评测，并在当前进程退出前完成该 record 的三项反馈计算。"""
    with recorder as recording:
        result = await adapter.run(case.question)

    # 先确认本次 record 的追踪事件已写入 PostgreSQL。
    recording.get()

    # TruLens 会针对本次 record 同步触发三项 Metric，并有界等待结果持久化。
    # 这避免 pytest 退出时后台 evaluator 线程尚未完成评分。
    feedback_results = recording.retrieve_feedback_results(timeout=feedback_timeout)
    return result, feedback_results


