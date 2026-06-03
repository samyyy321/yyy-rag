from unittest.mock import Mock

from src.api.dependencies import get_storage


def test_storage_dependency_reuses_client(monkeypatch):
    storage = Mock()
    factory = Mock(return_value=storage)
    monkeypatch.setattr("src.api.dependencies.get_object_storage", factory)

    assert get_storage() is storage
    assert get_storage() is storage
    factory.assert_called_once_with()
