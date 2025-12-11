import json
from pathlib import Path
from google import genai
from jinja2 import Environment, FileSystemLoader
from .prompt_builder import render_prompt
from google.genai import types


def generate_researcher_summary(
    info_completa_investigador: str,
    system_instruction_path: Path,
    prompt_path: Path,
    model_name: str = "gemini-2.5-flash"
) -> dict:
    """
    Generate structured researcher summary using Gemini models + Jinja templates.

    Parameters
    ----------
    info_completa_investigador : str
        Full concatenated information about the researcher.
    system_instruction_path : Path
        Path object pointing to the .jinja system instruction file.
    prompt_path : Path
        Path object pointing to the .jinja prompt template.

    Returns
    -------
    dict
        Dictionary containing the generated summary and keywords.
    """

    # Validate file existence
    if not system_instruction_path.exists():
        raise FileNotFoundError(f"System instruction missing: {system_instruction_path}")

    if not prompt_path.exists():
        raise FileNotFoundError(f"User prompt template missing: {prompt_path}")

    # Render templates
    system_instruction, prompt = render_prompt(
        system_instruction_path,
        prompt_path,
        info_completa_investigador
    )

    # Schema
    response_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "brief": types.Schema(type=types.Type.STRING),
            "profile": types.Schema(type=types.Type.STRING),
            "areas": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING)
            ),
        },
        required=["brief", "profile", "areas"],
    )

    client = genai.Client()

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_schema=response_schema,
        response_mime_type="application/json",
        temperature=0.7,
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config
        )
        return json.loads(response.text)

    except Exception as e:
        print("Error:", e)
        return {
            "brief": "Error generating brief.",
            "profile": "Error generating profile.",
            "areas": ["Error"]
        }