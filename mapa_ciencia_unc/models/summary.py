from typing import Optional
from pydantic import BaseModel, Field


class MultipleSummariesCreate(BaseModel):
    """
    Model for creating multiple summaries in bulk.

    The content_mapping keys can be either:
    - researcher_id (MongoDB ObjectId as string)
    - researcher_cuit (CUIT identifier as string)

    The endpoint will try researcher_id first, then fall back to CUIT lookup.
    """
    overwrite: bool = False
    model: str
    tag: str
    content_mapping: dict[str, str]  # Mapping of researcher identifier (ID or CUIT) to summary JSON string


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
