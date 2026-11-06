import pytest
from pydantic import ValidationError
from app.schemas import ProcessRequest

def test_valid_request():
    req = ProcessRequest(payload={'hello': 'world'}, preferred_provider='B')
    assert req.preferred_provider == 'B'

def test_invalid_provider():
    with pytest.raises(ValidationError):
        ProcessRequest(payload={}, preferred_provider='D')
