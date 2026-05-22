"""TruLens 评估适配器的本地单元测试，不调用任何远程服务。"""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage

from test.evaluation.trulens_doc_rag_adapter import (
    DocRagEvaluationAdapter,
    load_evaluation_cases,
)


class FakeLlm:
    """模拟回答模型，并保留最后一次收到的提示词。"""

    def __init__(self) -> None:
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        return AIMessage(content="Transformer 是一种注意力机制模型。")


@pytest.mark.asyncio
async def test_adapter_returns_the_contexts_used_to_generate_answer() -> None:
    """评估记录必须包含与回答完全相同的检索上下文。"""
    captured = {}

    async def fake_search(**kwargs):
        captured.update(kwargs)
        return [
            {"doc_name": "transformer.pdf", "page_number": 1, "text": "attention context"},
            {"doc_name": "transformer.pdf", "page_number": 2, "text": "encoder context"},
        ]

    llm = FakeLlm()
    adapter = DocRagEvaluationAdapter(
        embedding_model=object(),
        milvus_client=object(),
        llm=llm,
        search_function=fake_search,
    )

    record = await adapter.run("什么是 Transformer？")

    assert captured["top_k"] == 20
    assert captured["rerank_top_k"] == 5
    assert captured["use_hyde"] is True
    assert record.question == "什么是 Transformer？"
    assert record.contexts == ["attention context", "encoder context"]
    assert record.answer == "Transformer 是一种注意力机制模型。"
    assert "attention context" in llm.messages[0].content
    assert "encoder context" in llm.messages[0].content


def test_load_evaluation_cases_rejects_duplicate_ids(tmp_path) -> None:
    """评测集 ID 必须唯一，避免同一问题被重复统计。"""
    dataset_path = tmp_path / "cases.jsonl"
    dataset_path.write_text(
        "\n".join(
            [
                json.dumps({"id": "duplicate", "question": "第一个问题"}),
                json.dumps({"id": "duplicate", "question": "第二个问题"}),
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="重复"):
        load_evaluation_cases(dataset_path)


def test_load_evaluation_cases_reads_optional_expected_answer(tmp_path) -> None:
    """标准答案为后续 Ground Truth 评估预留，但首版不强制要求。"""
    dataset_path = tmp_path / "cases.jsonl"
    dataset_path.write_text(
        json.dumps(
            {
                "id": "transformer-definition",
                "question": "什么是 Transformer？",
                "expected_answer": "一种基于注意力机制的架构。",
            }
        ),
        encoding="utf-8",
    )

    cases = load_evaluation_cases(dataset_path)

    assert len(cases) == 1
    assert cases[0].id == "transformer-definition"
    assert cases[0].expected_answer == "一种基于注意力机制的架构。"


def test_build_trulens_feedbacks_configures_rag_triad() -> None:
    """评估配置必须同时包含检索相关性、回答相关性与事实支撑度。"""
    from langchain_openai import ChatOpenAI

    from test.evaluation.trulens_runner import build_trulens_feedbacks

    judge_llm = ChatOpenAI(
        model="judge-model",
        api_key="not-used-in-this-test",
        base_url="https://example.invalid/v1",
        temperature=0,
    )

    feedbacks = build_trulens_feedbacks(judge_llm)

    assert len(feedbacks) == 3
    assert {feedback.supplied_name for feedback in feedbacks} == {
        "Context Relevance",
        "Answer Relevance",
        "Groundedness",
    }


def test_load_evaluation_cases_accepts_utf8_bom(tmp_path) -> None:
    """PowerShell 默认写入 UTF-8 BOM 时，首条 JSONL 样本仍应可被读取。"""
    dataset_path = tmp_path / "cases-with-bom.jsonl"
    payload = json.dumps(
        {"id": "bom-case", "question": "UTF-8 BOM 是否兼容？"},
        ensure_ascii=False,
    )
    dataset_path.write_bytes(b"\xef\xbb\xbf" + payload.encode("utf-8"))

    cases = load_evaluation_cases(dataset_path)

    assert [case.id for case in cases] == ["bom-case"]
