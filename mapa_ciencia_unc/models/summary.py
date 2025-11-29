from beanie import Document
from pydantic import BaseModel


class MultipleSummariesCreate(BaseModel):
    model: str
    prompt_id: str
    content_mapping: dict[str, str]  # Mapping of researcher IDs to summary content


class Summary(Document):
    model: str
    prompt_id: str
    content: str
