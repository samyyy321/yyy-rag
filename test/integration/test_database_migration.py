import os

import pytest
from sqlalchemy import create_engine, inspect, text


pytestmark = pytest.mark.integration


def test_alembic_configuration_and_initial_migration_exist():
    from pathlib import Path

    assert Path("alembic.ini").is_file()
    assert Path("alembic/env.py").is_file()
    assert Path(
        "alembic/versions/20260911_160524_create_rag_business_tables.py"
    ).is_file()


def test_business_schema_has_comments_and_no_foreign_keys():
    url = os.environ.get("DATABASE_URL")
    if not url or not url.startswith("postgresql"):
        pytest.skip("需要 PostgreSQL DATABASE_URL 才运行")

    engine = create_engine(url)
    inspector = inspect(engine)
    assert set(inspector.get_table_names()).issuperset(
        {"knowledge_bases", "documents", "ingestion_tasks"}
    )
    assert inspector.get_foreign_keys("knowledge_bases") == []
    assert inspector.get_foreign_keys("documents") == []
    assert inspector.get_foreign_keys("ingestion_tasks") == []

    with engine.connect() as connection:
        table_comments = dict(connection.execute(text("""
            SELECT c.relname, obj_description(c.oid, 'pg_class')
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname IN ('knowledge_bases', 'documents', 'ingestion_tasks')
        """)).all())
        column_comments = connection.execute(text("""
            SELECT table_name, column_name, col_description(
                (table_schema || '.' || table_name)::regclass::oid,
                ordinal_position
            )
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ('knowledge_bases', 'documents', 'ingestion_tasks')
        """)).all()

    assert table_comments == {
        "knowledge_bases": "知识库主表",
        "documents": "文档主表，保存原始文件和导入状态",
        "ingestion_tasks": "文档导入任务表",
    }
    assert len(column_comments) == 26
    assert all(comment for _, _, comment in column_comments)
