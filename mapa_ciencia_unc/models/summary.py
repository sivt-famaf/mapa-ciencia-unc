from pydantic import BaseModel


class MultipleSummariesCreate(BaseModel):
    overwrite: bool = False
    model: str
    tag: str
    content_mapping: dict[str, str]  # Mapping of researcher IDs to summary content


class Summary(BaseModel):
    model: str
    tag: str
    content: str
