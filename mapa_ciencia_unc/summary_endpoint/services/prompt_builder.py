from pathlib import Path
from jinja2 import Environment, FileSystemLoader

def render_prompt(system_path: Path, prompt_path: Path, info: str) -> tuple[str, str]:
    """
    Generate rendered system instruction and main prompt.

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
    tuple[str, str]
        Rendered system instruction and main prompt.
    """

    # Load templates
    env_system = Environment(loader=FileSystemLoader(system_path.parent))
    env_prompt = Environment(loader=FileSystemLoader(prompt_path.parent))

    system_template = env_system.get_template(system_path.name)
    prompt_template = env_prompt.get_template(prompt_path.name)

    system_instruction = system_template.render()
    prompt = prompt_template.render(info_completa_investigador=info)

    return system_instruction, prompt