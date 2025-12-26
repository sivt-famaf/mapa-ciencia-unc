import json
from pathlib import Path
from google import genai
from jinja2 import Environment, FileSystemLoader
from .prompt_builder import render_prompt
from google.genai import types
from typing import List

from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.project import Project
from mapa_ciencia_unc.config import GEMINI_API_KEY


def generate_researcher_summary(
    info_completa_investigador: str,
    system_instruction_path: Path,
    prompt_path: Path,
    model_name: str = "gemini-2.5-flash",
) -> dict:
    """
    Generate structured researcher summary using Gemini models + Jinja templates.

    Args:
        info_completa_investigador : Full concatenated information about the researcher.
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
        system_instruction_path, prompt_path, info_completa_investigador
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
        print("Error:", e)
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

    for article in articles:
        publications_parts.append(article.titulo)

        if article.resumen:
            publications_parts.append(article.resumen)

    for project in projects:
        projects_parts.append(project.titulo_proyecto)

        if project.resumen_proyecto:
            projects_parts.append(project.resumen_proyecto)

    return {
        "projects": "\n\n".join(projects_parts),
        "publications": "\n\n".join(publications_parts),
    }
