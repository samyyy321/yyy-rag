from src.db.models import Base, Document, IngestionTask, KnowledgeBase


def test_business_tables_have_no_foreign_keys():
    assert list(KnowledgeBase.__table__.foreign_key_constraints) == []
    assert list(Document.__table__.foreign_key_constraints) == []
    assert list(IngestionTask.__table__.foreign_key_constraints) == []


def test_business_tables_have_comments_and_expected_columns():
    assert KnowledgeBase.__table__.comment == "知识库主表"
    assert Document.__table__.comment == "文档主表，保存原始文件和导入状态"
    assert IngestionTask.__table__.comment == "文档导入任务表"
    assert set(Document.__table__.columns.keys()) == {
        "id", "knowledge_base_id", "original_name", "object_key",
        "content_type", "file_size", "doc_type", "category", "status",
        "chunk_count", "error_message", "created_at", "updated_at",
    }
    assert all(
        column.comment
        for table in Base.metadata.sorted_tables
        for column in table.columns
    )
