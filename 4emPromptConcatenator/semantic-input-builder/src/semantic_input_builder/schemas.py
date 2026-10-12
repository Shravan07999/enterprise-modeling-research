from pydantic import BaseModel, Field


class Component(BaseModel):
    id: str | None = Field(default=None, description="Identifier like C1, C2")
    name: str = Field(description="Component name extracted from the scenario")
    type: str = Field(description="4EM component type (e.g. Business Process, Information Set, Goal, Role)")
    description: str = Field(default="", description="Semantic role or description")


class Relationship(BaseModel):
    id: str | None = Field(default=None, description="Identifier like R1, R2")
    source: str = Field(description="Name of source component")
    type: str = Field(description="Relationship type (e.g. is input to, has result, performs)")
    target: str = Field(description="Name of target component")
    description: str = Field(default="", description="Optional relationship context")


class SemanticExtraction(BaseModel):
    model_type: str = Field(description="4EM model key, e.g. business_process")
    components: list[Component] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
