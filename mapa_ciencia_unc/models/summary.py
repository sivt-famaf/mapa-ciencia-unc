import json
from typing import List, Optional
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
    areas: List[str] = Field(default_factory=list, description="Research areas extracted from summary")
    brief: str = Field(default="", description="Brief summary extracted from detailed summary")

    @classmethod
    def from_content(cls, model: str, tag: str, content: str) -> "Summary":
        """
        Create a Summary instance from content string.

        Tries to parse content as JSON and extract 'areas' and 'brief' fields.
        If parsing fails or fields don't exist, uses default values.

        Args:
            model: Model name used to generate the summary
            tag: Tag identifier for the summary
            content: Summary content (may be JSON string or plain text)

        Returns:
            Summary instance with extracted fields if available
        """
        areas = []
        brief = ""

        # Try to parse content as JSON
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                # Extract areas if present (should be a list)
                if "areas" in parsed and isinstance(parsed["areas"], list):
                    areas = [str(area) for area in parsed["areas"]]

                # Extract brief if present (should be a string)
                if "brief" in parsed and isinstance(parsed["brief"], str):
                    brief = parsed["brief"]

                if "profile" in parsed and isinstance(parsed["profile"], str):
                    content = parsed["profile"]
        except (json.JSONDecodeError, TypeError):
            # If content is not valid JSON, just use it as-is in content field
            pass

        return cls(
            model=model,
            tag=tag,
            content=content,
            areas=areas,
            brief=brief,
        )


class SummaryRequest(BaseModel):
    researcher_id: str
    system_name: Optional[str] = Field(
        default="v1/system_instruction_1",
        description="System instruction name (optional for Ollama)",
    )
    prompt_name: str = Field(default="v1/prompt_1")
    tag: str
    model: str
    max_articles: Optional[int] = Field(
        default=None, description="Maximum number of articles to include"
    )
    max_articles_length: Optional[int] = Field(
        default=None, description="Maximum number of words per article abstract"
    )
    max_projects: Optional[int] = Field(
        default=None, description="Maximum number of projects to include"
    )
    max_projects_length: Optional[int] = Field(
        default=None, description="Maximum number of words per project summary"
    )
    max_intros: Optional[int] = Field(
        default=None, description="Maximum number of project intros to include"
    )
    max_intros_length: Optional[int] = Field(
        default=None, description="Maximum number of words per project intro"
    )
