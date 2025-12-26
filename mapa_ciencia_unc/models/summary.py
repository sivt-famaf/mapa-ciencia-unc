from typing import Optional
from pydantic import BaseModel, Field


class MultipleSummariesCreate(BaseModel):
    overwrite: bool = False
    model: str
    tag: str
    content_mapping: dict[str, str]  # Mapping of researcher IDs to summary content


class Summary(BaseModel):
    model: str
    tag: str
    content: str


class SummaryRequest(BaseModel):
    researcher_id: str
    system_name: Optional[str] = Field(
        default="v1/system_instruction_1",
        description="System instruction name (optional for Ollama)",
    )
    prompt_name: str = Field(default="v1/prompt_1")
    tag: str
    model: str
