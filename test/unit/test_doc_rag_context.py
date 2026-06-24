from src.query.doc_rag import format_doc_context
from src.query.prompts import DOC_QA_PROMPT


def test_format_doc_context_keeps_source_name_without_page_metadata():
    """传给模型的上下文应保留文档来源，但不得携带页码信息。"""
    context = format_doc_context(
        [
            {
                "doc_name": "指南.pdf",
                "page_number": 0,
                "text": "相关文档片段",
            }
        ]
    )

    assert context == "文档片段1 【来源：指南.pdf】：\n相关文档片段"
    assert "页码未提供" not in context
    assert "第0页" not in context


def test_doc_qa_prompt_requires_source_name_without_page_output():
    """聊天回答应内联标注文档来源，但不得输出页码等定位信息。"""
    assert "回答中必须内联标注来源，格式：【来源：文档名称】" in DOC_QA_PROMPT
    assert "不要输出页码、页码未提供、分块序号或相似度" in DOC_QA_PROMPT
    assert "第X页" not in DOC_QA_PROMPT