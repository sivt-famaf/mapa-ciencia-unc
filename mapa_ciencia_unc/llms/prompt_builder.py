from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import Mapping, Any

def render_prompt(
    system_path: Path, 
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
    env_system = Environment(loader=FileSystemLoader(system_path.parent))
    env_prompt = Environment(loader=FileSystemLoader(prompt_path.parent))

    system_template = env_system.get_template(system_path.name)
    prompt_template = env_prompt.get_template(prompt_path.name)

    system_instruction = system_template.render()
    prompt = prompt_template.render(**context)

    return system_instruction, prompt