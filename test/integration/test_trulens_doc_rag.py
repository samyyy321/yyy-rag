"""显式执行的 TruLens 文档 RAG 集成评测。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.infra.embedding import get_embedding_model
from src.infra.llm import get_llm
from src.infra.milvus_client import get_milvus_client
from test.evaluation.trulens_doc_rag_adapter import (
    DocRagEvaluationAdapter,
    load_evaluation_cases,
)
from test.evaluation.trulens_runner import (
    create_trulens_recorder,
    get_evaluation_llm,
    run_evaluation_case_with_feedback,
)


pytestmark = pytest.mark.integration
DATASET_PATH = Path(__file__).parents[1] / "evaluation" / "data" / "doc_rag_eval.jsonl"


def _get_case_limit() -> int:
    """读取本次评测样本上限；默认一条以控制远程模型调用成本。"""
    value = os.getenv("TRULENS_CASE_LIMIT", "1")
    try:
        limit = int(value)
    except ValueError as exc:
        raise ValueError("TRULENS_CASE_LIMIT 必须是非负整数") from exc
    if limit < 0:
        raise ValueError("TRULENS_CASE_LIMIT 必须是非负整数")
    return limit


@pytest.mark.asyncio
async def test_doc_rag_with_trulens() -> None:
    """对真实 RAG 链路记录 RAG Triad；必须由环境变量显式解锁。"""

    cases = load_evaluation_cases(DATASET_PATH)
    limit = _get_case_limit()
    selected_cases = cases if limit == 0 else cases[:limit]
    if not selected_cases:
        pytest.skip("TRULENS_CASE_LIMIT 选择了 0 条样本")

    adapter = DocRagEvaluationAdapter(
        embedding_model=get_embedding_model(),
        milvus_client=get_milvus_client(),
        llm=get_llm(),
    )
    recorder = create_trulens_recorder(adapter, get_evaluation_llm())

    expected_metrics = {
        "Context Relevance",
        "Answer Relevance",
        "Groundedness",
    }
    completed = []
    for case in selected_cases:
        record, feedback_results = await run_evaluation_case_with_feedback(
            recorder,
            adapter,
            case,
        )
        assert record.question == case.question
        assert record.contexts, f"样本 {case.id} 没有检索到上下文"
        assert record.answer.strip(), f"样本 {case.id} 没有生成回答"
        assert expected_metrics.issubset(feedback_results.columns), (
            f"样本 {case.id} 未完成全部 RAG Triad 评分: {feedback_results.columns.tolist()}"
        )
        assert not feedback_results.empty, f"样本 {case.id} 没有反馈评分结果"
        assert feedback_results.loc[:, sorted(expected_metrics)].notna().all().all(), (
            f"样本 {case.id} 存在未完成的 RAG Triad 评分"
        )
        completed.append(case.id)

    assert completed, "没有完成任何评测样本"


