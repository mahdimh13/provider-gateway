from typing import Any
from pydantic import BaseModel, Field

class ProcessRequest(BaseModel):
    payload: dict[str, Any] = Field(..., description='JSON payload forwarded unchanged to the provider')
    preferred_provider: str | None = Field(default=None, pattern='^[ABC]$')

class ProcessResponse(BaseModel):
    request_id: str
    trace_id: str
    provider: str
    provider_status: int
    duration_ms: float
    result: Any
