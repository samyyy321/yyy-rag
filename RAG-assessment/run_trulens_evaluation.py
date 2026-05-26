"""运行完整 TruLens 文档 RAG 评测集。"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.trulens_doc_rag_adapter import (
    DocRagEvaluationAdapter,
    load_evaluation_cases,
)
from src.evaluation.trulens_runner import (
    create_trulens_recorder,
    get_evaluation_llm,
    run_evaluation_case_with_feedback,
)
from src.infra.embedding import get_embedding_model
from src.infra.llm import get_llm
from src.infra.milvus_client import get_milvus_client


DATASET_PATH = PROJECT_ROOT / "RAG-assessment" / "data" / "doc_rag_eval.jsonl"
METRIC_NAMES = ("Context Relevance", "Answer Relevance", "Groundedness")


def get_case_limit() -> int:
    """读取样本数量限制；0 表示运行全部评测样本。"""
    raw_value = os.getenv("TRULENS_CASE_LIMIT", "1")
    try:
        limit = int(raw_value)
    except ValueError as exc:
        raise ValueError("TRULENS_CASE_LIMIT 必须是非负整数") from exc
    if limit < 0:
        raise ValueError("TRULENS_CASE_LIMIT 必须是非负整数")
    return limit


async def run_assessment() -> int:
    """执行评测集，并在每个样本完成三项指标后打印结果。"""
    if os.getenv("RUN_TRULENS_EVAL") != "1":
        raise RuntimeError("请先设置 RUN_TRULENS_EVAL=1，显式确认执行远程评测")

    cases = load_evaluation_cases(DATASET_PATH)
    limit = get_case_limit()
    selected_cases = cases if limit == 0 else cases[:limit]
    if not selected_cases:
        raise RuntimeError("没有可评测的样本")

    adapter = DocRagEvaluationAdapter(
        embedding_model=get_embedding_model(),
        milvus_client=get_milvus_client(),
        llm=get_llm(),
    )
    recorder = create_trulens_recorder(adapter, get_evaluation_llm())

    for case in selected_cases:
        record, feedback_results = await run_evaluation_case_with_feedback(
            recorder,
            adapter,
            case,
        )
        scores = {
            name: float(feedback_results.iloc[0][name])
            for name in METRIC_NAMES
        }
        print(f"[{case.id}] {record.question}")
        print("  " + ", ".join(f"{name}={scores[name]:.6f}" for name in METRIC_NAMES))

    return 0


def main() -> int:
    """加载项目配置并启动异步评测。"""
    load_dotenv(PROJECT_ROOT / ".env")
    return asyncio.run(run_assessment())


if __name__ == "__main__":
    raise SystemExit(main())
