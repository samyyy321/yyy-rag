from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.services.knowledge_base_service import (
    ResourceConflictError,
    ResourceNotFoundError,
    delete_knowledge_base,
    get_knowledge_base,
)


def test_get_missing_knowledge_base_raises_not_found():
    db = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    with pytest.raises(ResourceNotFoundError):
        get_knowledge_base(db, uuid4())


def test_delete_knowledge_base_locks_row_before_counting_documents():
    kb = Mock()
    row_result = Mock()
    row_result.scalar_one_or_none.return_value = kb
    count_result = Mock()
    count_result.scalar_one.return_value = 1
    db = Mock()
    db.execute.side_effect = [row_result, count_result]

    with pytest.raises(ResourceConflictError):
        delete_knowledge_base(db, uuid4())

    statement = db.execute.call_args_list[0].args[0]
    assert statement._for_update_arg is not None
    db.rollback.assert_called_once()
