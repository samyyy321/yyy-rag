from unittest.mock import Mock

from src.services.chat_service import check_health


def test_check_health_calls_all_dependencies_when_available():
    db = Mock()
    storage = Mock()
    milvus = Mock()
    assert check_health(db, storage, milvus) is True
    db.execute.assert_called_once()
    storage.ensure_bucket.assert_called_once()
    milvus.list_collections.assert_called_once()
