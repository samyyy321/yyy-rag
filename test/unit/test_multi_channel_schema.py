import pytest
from pydantic import ValidationError

from src.api.schemas import ChatRequest


@pytest.mark.parametrize("channels", [["graph"], ["sql"], ["graph", "sql"]])
def test_chat_request_allows_non_document_channels_without_knowledge_base(channels):
    """纯图谱、SQL 或二者融合请求不应依赖文档知识库。"""
    payload = ChatRequest(question="测试问题", channels=channels)

    assert payload.knowledge_base_id is None
    assert payload.channels == channels


def test_chat_request_defaults_to_document_channel():
    """未指定通道时，应保持原有的文档 RAG 行为。"""
    payload = ChatRequest(
        knowledge_base_id="00000000-0000-0000-0000-000000000001",
        question="测试问题",
    )

    assert payload.channels == ["document"]


def test_chat_request_accepts_document_and_graph_with_knowledge_base():
    """选择文档融合图谱时必须携带知识库 ID。"""
    payload = ChatRequest(
        knowledge_base_id="00000000-0000-0000-0000-000000000001",
        question="测试问题",
        channels=["document", "graph"],
    )

    assert payload.channels == ["document", "graph"]


@pytest.mark.parametrize("channels", [["document"], ["document", "graph"]])
def test_chat_request_requires_knowledge_base_for_document_channel(channels):
    """任何包含 document 的请求缺失知识库时必须失败。"""
    with pytest.raises(ValidationError, match="document 通道需要 knowledge_base_id"):
        ChatRequest(question="测试问题", channels=channels)


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