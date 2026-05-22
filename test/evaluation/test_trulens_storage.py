"""TruLens PostgreSQL 存储与 Dashboard 配置的单元测试。"""

from __future__ import annotations

import pytest

from test.evaluation.trulens_runner import create_trulens_session
from test.evaluation.run_trulens_dashboard import get_dashboard_options


def test_create_trulens_session_passes_postgresql_url_to_factory() -> None:
    """配置 PostgreSQL URL 后，Session 工厂必须收到同一 URL。"""
    captured = {}

    def fake_session_factory(**kwargs):
        captured.update(kwargs)
        return "postgres-session"

    database_url = "postgresql+psycopg://rag:rag@localhost:5432/trulens"
    session = create_trulens_session(
        environ={"TRULENS_DATABASE_URL": database_url},
        session_factory=fake_session_factory,
    )

    assert session == "postgres-session"
    assert captured == {"database_url": database_url}


def test_create_trulens_session_falls_back_to_default_database() -> None:
    """未配置 URL 时必须保留 SQLite 默认回退，方便本地单测。"""
    captured = {}

    def fake_session_factory(**kwargs):
        captured.update(kwargs)
        return "sqlite-session"

    session = create_trulens_session(environ={}, session_factory=fake_session_factory)

    assert session == "sqlite-session"
    assert captured == {}


def test_dashboard_options_default_to_loopback_address() -> None:
    """Dashboard 默认不得监听全部网卡，避免无意暴露评测数据。"""
    options = get_dashboard_options(environ={})

    assert options.host == "127.0.0.1"
    assert options.port == 8501


@pytest.mark.parametrize("port", ["0", "65536", "not-a-number"])
def test_dashboard_options_reject_invalid_port(port: str) -> None:
    """错误端口必须在启动前被拒绝，而不是交给 Dashboard 运行时失败。"""
    with pytest.raises(ValueError, match="端口"):
        get_dashboard_options(environ={"TRULENS_DASHBOARD_PORT": port})


def test_evaluation_record_serialization_keeps_answer_and_contexts_for_otel_metrics() -> None:
    """OTel 的主输出必须携带答案和上下文，避免指标只收到问题字符串。"""
    from test.evaluation.trulens_runner import (
        RagTriadJudge,
        serialize_evaluation_record,
    )

    serialized = serialize_evaluation_record(
        {"question": "什么是 Transformer？", "contexts": ["上下文一"], "answer": "注意力模型"}
    )

    contexts, answer = RagTriadJudge._record_values(serialized)

    assert contexts == ["上下文一"]
    assert answer == "注意力模型"


def test_dashboard_command_uses_current_python_to_run_streamlit() -> None:
    """启动器不能依赖 PATH 中可能属于其他环境的 streamlit.exe。"""
    from test.evaluation.run_trulens_dashboard import (
        DashboardOptions,
        build_dashboard_command,
    )

    command = build_dashboard_command(
        DashboardOptions(
            database_url="postgresql+psycopg://rag:rag@localhost:5432/trulens",
            host="127.0.0.1",
            port=8501,
        ),
        python_executable="C:/env/python.exe",
        dashboard_main_path="C:/env/site-packages/trulens/dashboard/main.py",
    )

    assert command[:4] == ["C:/env/python.exe", "-m", "streamlit", "run"]
    assert "--database-url" in command
    assert "--database-prefix" in command
    assert "trulens_" in command

class _FakeJudgeResponse:
    """模拟 LangChain 裁判模型响应。"""

    def __init__(self, content: str) -> None:
        self.content = content


class _FakeJudgeLlm:
    """按顺序返回预设评分文本，避免单元测试调用远程模型。"""

    def __init__(self, contents: list[str]) -> None:
        self.contents = iter(contents)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return _FakeJudgeResponse(next(self.contents))


def test_rag_triad_judge_retries_once_when_score_is_out_of_range() -> None:
    """裁判首次返回 4 分时必须重试，并只接受 0 到 3 的严格 JSON 评分。"""
    from test.evaluation.trulens_runner import RagTriadJudge

    llm = _FakeJudgeLlm(
        [
            '{"score": 4, "reason": "超出范围"}',
            '{"score": 3, "reason": "回答完整回应问题"}',
        ]
    )
    judge = RagTriadJudge(llm_factory=lambda: llm)

    score, reasons = judge.answer_relevance(
        "什么是 Transformer？",
        {"contexts": ["Transformer 使用注意力机制。"], "answer": "Transformer 是注意力模型。"},
    )

    assert score == 1.0
    assert reasons["reason"] == "回答完整回应问题"
    assert llm.calls == 2


def test_evaluation_llm_uses_bounded_timeout() -> None:
    """裁判模型请求必须设置超时，避免评分任务永久阻塞评测进程。"""
    from test.evaluation.trulens_runner import get_evaluation_llm

    llm = get_evaluation_llm()

    assert llm.request_timeout == 90
    assert llm.max_retries == 1

@pytest.mark.asyncio
async def test_run_evaluation_case_with_feedback_waits_for_current_record_only() -> None:
    """完整评测必须等待本次 record 的三项反馈，不能依赖后台线程在 pytest 退出后继续执行。"""
    from test.evaluation.trulens_runner import run_evaluation_case_with_feedback
    from test.evaluation.trulens_doc_rag_adapter import EvaluationCase

    class FakeRecording:
        def __init__(self) -> None:
            self.get_called = False
            self.timeout = None

        def get(self):
            self.get_called = True
            return object()

        def retrieve_feedback_results(self, timeout: float):
            self.timeout = timeout
            return {"Context Relevance": 1.0, "Answer Relevance": 2 / 3, "Groundedness": 1.0}

    class FakeRecorder:
        def __init__(self) -> None:
            self.recording = FakeRecording()

        def __enter__(self):
            return self.recording

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    class FakeAdapter:
        async def run(self, question: str):
            return {"question": question, "contexts": ["context"], "answer": "answer"}

    record, feedbacks = await run_evaluation_case_with_feedback(
        FakeRecorder(),
        FakeAdapter(),
        EvaluationCase(id="case-1", question="问题"),
        feedback_timeout=45,
    )

    assert record["answer"] == "answer"
    assert feedbacks["Groundedness"] == 1.0


def test_create_recorder_disables_background_evaluator_for_explicit_evaluation(monkeypatch) -> None:
    """完整评测只计算当前 record，不能启动会扫描历史记录的后台 evaluator。"""
    import test.evaluation.trulens_runner as runner

    captured = {}

    class FakeTruApp:
        def __init__(self, *args, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(runner, "DocRagTruApp", FakeTruApp)

    runner.create_trulens_recorder(
        adapter=object(),
        judge_llm=object(),
        session=object(),
    )

    assert captured["start_evaluator"] is False

