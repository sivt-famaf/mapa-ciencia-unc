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
    system_name: str = Field(default="system_instruction_1")
    prompt_name: str = Field(default="v1/prompt_1.jinja")
    tag: str
    model: str
