from pydantic import BaseModel
from typing import Optional

class SummaryRequest(BaseModel):
    dataset_path: str
    limit: Optional[int] = 10
    include_articles: bool = False
    include_calls: bool = False
    include_projects: bool = False
    include_convenios: bool = False
    include_pdfs: bool = False
    system_name:str
    prompt_name: str