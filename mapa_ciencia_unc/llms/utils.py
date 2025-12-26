import json
import re
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import List, Mapping, Any, Optional

from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.project import Project


logger = logging.getLogger(__name__)


def clean_and_parse_json(text: str) -> Optional[dict]:
    """
    Clean and parse JSON from LLM responses that may contain markdown code blocks
    or other formatting artifacts.

    This function tries multiple strategies to extract and parse JSON:
    1. Remove markdown code blocks (```json, ```)
    2. Extract JSON from text using regex patterns
    3. Strip whitespace and try parsing
    4. Find the first { or [ and parse from there

    Args:
        text: Raw text response from LLM that should contain JSON

    Returns:
        Parsed JSON as a dictionary, or None if parsing fails

    Raises:
        ValueError: If JSON cannot be parsed after trying all strategies
    """
    # Note: This entire funcion is generated with AI, if buggy feel free to
    # delete it.
    if not text or not isinstance(text, str):
        raise ValueError("Input must be a non-empty string")

    original_text = text
    strategies_tried = []

    # Strategy 1: Remove markdown code blocks
    try:
        # Remove ```json or ``` at the start
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', text.strip(), flags=re.MULTILINE)
        # Remove ``` at the end
        cleaned = re.sub(r'\n?```\s*$', '', cleaned.strip(), flags=re.MULTILINE)

        parsed = json.loads(cleaned)
        logger.debug("Successfully parsed JSON after removing markdown code blocks")
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        strategies_tried.append(f"Remove markdown blocks: {str(e)}")

    # Strategy 2: Find JSON object/array using regex
    try:
        # Look for content between first { and last }
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            logger.debug("Successfully parsed JSON using regex extraction (object)")
            return parsed

        # Try array syntax
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            logger.debug("Successfully parsed JSON using regex extraction (array)")
            return parsed
    except (json.JSONDecodeError, ValueError) as e:
        strategies_tried.append(f"Regex extraction: {str(e)}")

    # Strategy 3: Strip all leading/trailing whitespace and common prefixes
    try:
        # Remove common text patterns that LLMs might add
        patterns_to_remove = [
            r'^Here is the JSON:?\s*\n?',
            r'^Here\'s the JSON:?\s*\n?',
            r'^JSON:?\s*\n?',
            r'^Response:?\s*\n?',
            r'^Output:?\s*\n?',
        ]
        cleaned = text
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        cleaned = cleaned.strip()
        parsed = json.loads(cleaned)
        logger.debug("Successfully parsed JSON after removing common prefixes")
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        strategies_tried.append(f"Remove prefixes: {str(e)}")

    # Strategy 4: Find first { or [ and parse from there to the end
    try:
        # Find the first occurrence of { or [
        start_idx = -1
        for char in ['{', '[']:
            idx = text.find(char)
            if idx != -1 and (start_idx == -1 or idx < start_idx):
                start_idx = idx

        if start_idx != -1:
            # Try to find matching closing bracket
            substring = text[start_idx:]
            parsed = json.loads(substring)
            logger.debug("Successfully parsed JSON from first bracket to end")
            return parsed
    except (json.JSONDecodeError, ValueError) as e:
        strategies_tried.append(f"Parse from first bracket: {str(e)}")

    # Strategy 5: Try to extract just the JSON part line by line
    try:
        lines = text.split('\n')
        # Find first line with { or [
        start_line = -1
        end_line = -1

        for i, line in enumerate(lines):
            if start_line == -1 and ('{' in line or '[' in line):
                start_line = i
            if start_line != -1 and ('}' in line or ']' in line):
                end_line = i

        if start_line != -1 and end_line != -1:
            json_lines = lines[start_line:end_line + 1]
            json_text = '\n'.join(json_lines)
            parsed = json.loads(json_text)
            logger.debug("Successfully parsed JSON using line-by-line extraction")
            return parsed
    except (json.JSONDecodeError, ValueError) as e:
        strategies_tried.append(f"Line-by-line extraction: {str(e)}")

    # All strategies failed
    error_msg = f"Failed to parse JSON after trying {len(strategies_tried)} strategies:\n"
    error_msg += "\n".join(f"  - {s}" for s in strategies_tried)
    error_msg += f"\n\nOriginal text (first 500 chars):\n{original_text[:500]}"

    logger.error(error_msg)
    raise ValueError(error_msg)


def render_prompt(
    system_path: Path | None,
    prompt_path: Path,
    context: Mapping[str, Any],
) -> tuple[str, str]:
    """
    Args:
        system_path: Path to the .jinja system instruction file.
        prompt_path: Path to the .jinja prompt template.
        context: Dictionary with variables to be injected into the prompt template.

    Returns:
        Tuple with rendered system instruction and main prompt.
    """
    # Load templates
    if system_path:
        env_system = Environment(loader=FileSystemLoader(system_path.parent))
        system_template = env_system.get_template(system_path.name)
        system_instruction = system_template.render()
    else:
        system_instruction = ""

    env_prompt = Environment(loader=FileSystemLoader(prompt_path.parent))
    prompt_template = env_prompt.get_template(prompt_path.name)
    prompt = prompt_template.render(**context)

    return system_instruction, prompt


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
