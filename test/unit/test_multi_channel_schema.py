import pytest
from pydantic import ValidationError

from src.api.schemas import ChatRequest


def test_chat_request_defaults_to_document_channel():
    """未指定通道时，应保持原有的文档 RAG 行为。"""
    payload = ChatRequest(
        knowledge_base_id="00000000-0000-0000-0000-000000000001",
        question="测试问题",
    )

    assert payload.channels == ["document"]


def test_chat_request_accepts_graph_and_sql_channels():
    """允许调用方显式选择图谱与 SQL 通道。"""
    payload = ChatRequest(
        knowledge_base_id="00000000-0000-0000-0000-000000000001",
        question="测试问题",
        channels=["graph", "sql"],
    )

    assert payload.channels == ["graph", "sql"]


@pytest.mark.parametrize(
    "channels",
    [[], ["document", "document"], ["unknown"]],
)
def test_chat_request_rejects_invalid_channels(channels):
    """通道必须非空、唯一且属于受支持的固定集合。"""
    with pytest.raises(ValidationError):
        ChatRequest(
            knowledge_base_id="00000000-0000-0000-0000-000000000001",
            question="测试问题",
            channels=channels,
        )
