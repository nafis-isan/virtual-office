from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskCreate(BaseModel):
    instruction: str = Field(min_length=1, max_length=4000)

    @field_validator("instruction")
    @classmethod
    def require_non_whitespace_instruction(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Instruksi tidak boleh kosong.")
        return cleaned


class TaskCreated(BaseModel):
    id: int
    status: str


class StepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    agent_name: str
    title: str
    expected_output: str
    status: str
    output: str | None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender: str
    content: str
    created_at: datetime


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instruction: str
    status: str
    summary: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class TaskDetail(TaskRead):
    steps: list[StepRead]
    messages: list[MessageRead]


class TaskSummary(TaskRead):
    pass


class AgentRead(BaseModel):
    name: str
    display_name: str
    role: str
    status: str


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_name: str
    status: str
    message: str
    created_at: datetime


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_id: int
    name: str
    content: str
    created_at: datetime


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)
