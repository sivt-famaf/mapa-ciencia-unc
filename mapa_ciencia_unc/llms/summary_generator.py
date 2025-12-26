import json
import logging
from pathlib import Path
from google import genai
from google.genai import types
from typing import List

from mapa_ciencia_unc.llms.prompt_builder import render_prompt
from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.project import Project
from mapa_ciencia_unc.config import GEMINI_API_KEY


logger = logging.getLogger(__name__)


def generate_researcher_summary(
    full_researcher_info: str,
    system_instruction_path: Path,
    prompt_path: Path,
    model_name: str = "gemini-2.5-flash",
) -> dict:
    """
    Generate structured researcher summary using Gemini models + Jinja templates.

    Args:
        full_researcher_info : Full concatenated information about the researcher.
        system_instruction_path : Path object pointing to the .jinja system instruction file.
        prompt_path : Path object pointing to the .jinja prompt template.

    Returns:
        Dictionary containing the generated summary and keywords.
    """

    # Validate file existence
    if not system_instruction_path.exists():
        raise FileNotFoundError(
            f"System instruction missing: {system_instruction_path}"
        )

    if not prompt_path.exists():
        raise FileNotFoundError(f"User prompt template missing: {prompt_path}")

    # Render templates
    system_instruction, prompt = render_prompt(
        system_instruction_path, prompt_path, full_researcher_info
    )

    # Schema
    response_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "brief": types.Schema(type=types.Type.STRING),
            "profile": types.Schema(type=types.Type.STRING),
            "areas": types.Schema(
                type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)
            ),
        },
        required=["brief", "profile", "areas"],
    )
    client = genai.Client(api_key=GEMINI_API_KEY)

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_schema=response_schema,
        response_mime_type="application/json",
        temperature=0.7,
    )

    try:
        response = client.models.generate_content(
            model=model_name, contents=prompt, config=config
        )
        return json.loads(response.text)

    except Exception as e:
        logger.error("Error creating summary:", e)
        return {
            "brief": "Error generating brief.",
            "profile": "Error generating profile.",
            "areas": ["Error"],
        }


def build_researcher_llm_inputs(
    articles: List[Article],
    projects: List[Project],
) -> dict[str, str]:
    """
    Build separated textual inputs for projects and publications
    to be injected into a Jinja template.

    Args:
        articles: List of articles (publications) associated with a researcher.
            Only the title and abstract are used.
        projects: List of projects associated with a researcher.
            Only the project title and summary are used.

    Returns:
        Dictionary with two keys:
            - "projects": concatenated text of project titles and summaries.
            - "publications": concatenated text of article titles and abstracts.
    """

    publications_parts: list[str] = []
    projects_parts: list[str] = []

    for article in sorted(articles, key=lambda x: x.year, reverse=True):
        publications_parts.append("Título: " + article.titulo + f" ({article.year}) ")

        if article.resumen:
            publications_parts.append("Abstract: " + article.resumen)

    def project_year(project):
        if project.fecha_alta and hasattr(project.fecha_alta, "year"):
            return project.fecha_alta.year
        else:
            return None

    for project in sorted(projects, key=project_year, reverse=True):
        projects_parts.append(
            "Título: " + project.titulo_proyecto + f" ({project_year(project)})"
        )

        if project.resumen_proyecto:
            projects_parts.append(project.resumen_proyecto)

    return {
        "projects": "\n\n".join(projects_parts),
        "publications": "\n\n".join(publications_parts),
    }
