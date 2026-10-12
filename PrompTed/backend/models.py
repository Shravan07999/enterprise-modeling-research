from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone
from enum import Enum


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    ARCHITECT = "architect"
    PROMPT_ENGINEER = "prompt_engineer"


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    full_name: Optional[str] = None
    role: UserRole = Field(default=UserRole.ARCHITECT)


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=_utc_now)


class UserRead(UserBase):
    id: int
    created_at: datetime


class PromptBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    template: str
    input_variables: str
    tags: Optional[str] = None
    model_config_json: Optional[str] = None


class Prompt(PromptBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class ChainBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    framework: str = Field(default="General", index=True)


class Chain(ChainBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    steps: List["ChainStep"] = Relationship(back_populates="chain")


class ChainStepBase(SQLModel):
    chain_id: int = Field(foreign_key="chain.id")
    prompt_id: int = Field(foreign_key="prompt.id")
    order: int
    input_mapping: Optional[str] = None
    is_critic: bool = Field(default=False)
    output_schema: Optional[str] = None


class ChainStep(ChainStepBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    chain: Chain = Relationship(back_populates="steps")
    prompt: Prompt = Relationship()


class ExecutionHistoryBase(SQLModel):
    prompt_id: int = Field(foreign_key="prompt.id")
    inputs: str
    result: str
    created_at: datetime = Field(default_factory=_utc_now)


class ExecutionHistory(ExecutionHistoryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    metrics_json: Optional[str] = None
    prompt: Prompt = Relationship()


class PromptRead(PromptBase):
    id: int
    created_at: datetime
    updated_at: datetime


class ChainStepRead(ChainStepBase):
    id: int
    prompt: Optional[PromptRead] = None


class ChainRead(ChainBase):
    id: int
    created_at: datetime
    updated_at: datetime
    steps: List[ChainStepRead] = []


class ExecutionHistoryRead(ExecutionHistoryBase):
    id: int
    created_at: datetime
    prompt: Optional[PromptRead] = None
    metrics: Optional[dict] = None


class AuditLogBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    action: str
    target_type: str
    target_id: int
    details: str


class AuditLog(AuditLogBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_utc_now)
    user: "User" = Relationship()


class AuditLogRead(AuditLogBase):
    id: int
    created_at: datetime
    user: Optional[UserRead] = None


class ExportLogBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    format: str
    chain_name: str
    history_id: Optional[int] = None
    status: str
    error: Optional[str] = None
    entity_count: Optional[int] = None
    relation_count: Optional[int] = None
    duration_ms: Optional[int] = None


class ExportLog(ExportLogBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    created_at: datetime = Field(default_factory=_utc_now)


class ExportLogRead(ExportLogBase):
    id: int
    created_at: datetime
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
