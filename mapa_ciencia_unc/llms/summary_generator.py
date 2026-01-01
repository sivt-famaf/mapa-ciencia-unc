import json
import logging
import requests

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from google import genai
from google.genai import types

from mapa_ciencia_unc.llms.utils import render_prompt, clean_and_parse_json
from mapa_ciencia_unc.config import GEMINI_API_KEY, OLLAMA_HOST, OLLAMA_API_KEY


logger = logging.getLogger(__name__)


class SummaryGenerator:
    """Factory class for SummaryGenerators."""

    @classmethod
    def generate_researcher_summary(
        cls,
        context: str,
        system_instruction_path: Path,
        prompt_path: Path,
        model_name: str = "gemini-2.5-flash",
    ):
        """
        Generate structured researcher summary using LLM models + Jinja templates.

        Args:
            context : Full concatenated information about the researcher.
            system_instruction_path : Path object pointing to the .jinja system instruction file.
            prompt_path : Path object pointing to the .jinja prompt template.
            model_name : Name of the model to use (e.g., "gemini-2.5-flash" or "ollama")

        Returns:
            Dictionary containing the generated summary and keywords.
        """
        if model_name == "full-text":
            return SummaryGeneratorFullText.generate_researcher_summary(
                context, prompt_path
            )
        elif "gemini" in model_name:
            return SummaryGeneratorGemini.generate_researcher_summary(
                context, system_instruction_path, prompt_path, model_name
            )
        elif ("ollama" in model_name) or ("gemma" in model_name):
            return SummaryGeneratorOllama.generate_researcher_summary(
                context, prompt_path, model_name
            )
        else:
            raise ValueError(f"Model {model_name} not supported.")


class SummaryGeneratorGemini:

    @classmethod
    def generate_researcher_summary(
        cls,
        context: str,
        system_instruction_path: Path,
        prompt_path: Path,
        model_name: str = "gemini-2.5-flash",
    ) -> dict:
        # Render templates - Make sure prompt corresponds to schema
        system_instruction, prompt = render_prompt(
            system_instruction_path, prompt_path, context
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


class SummaryGeneratorOllama:

    @classmethod
    def generate_completion(cls, prompt, model):
        url = f"{OLLAMA_HOST}/api/chat/completions"
        headers = {
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        logger.info("Sending request to Ollama API...")
        response = requests.post(url, headers=headers, json=data, timeout=300)
        return response.json()

    @classmethod
    def extract_response(cls, response):
        try:
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error("Error in Ollama model output")
            raise e

    @classmethod
    def generate_researcher_summary(
        cls,
        context: str,
        prompt_path: Path,
        model_name: str = "gemma3:4b",
    ) -> dict:
        """
        Generate structured researcher summary using Ollama models via remote HTTP API.

        Args:
            context: Full concatenated information about the researcher.
            prompt_path: Path object pointing to the .jinja prompt template
                (combined prompt for Ollama).
            model_name: Name identifier.

        Returns:
            Dictionary containing the generated summary and keywords.
        """
        # For Ollama, we use a combined prompt template that includes both system instruction
        # and user prompt. We only render the prompt_path and ignore system_instruction_path.
        _, full_prompt = render_prompt(
            system_path=None, prompt_path=prompt_path, context=context
        )

        # Prepare the request to Ollama API
        try:
            response = cls.generate_completion(prompt=full_prompt, model=model_name)
            response_text = cls.extract_response(response)
        except Exception as e:
            logger.error("Error calling Ollama API:")
            raise e

        # Parse the JSON response using robust cleaning function
        try:
            parsed_response = clean_and_parse_json(response_text)
        except ValueError as e:
            logger.error("Error parsing Ollama response as JSON")
            raise e

        # Rename fields
        if parsed_response:
            parsed_response = {
                "brief": parsed_response.get("resumen", "Resumen no disponible."),
                "profile": parsed_response.get("perfil", "Perfil no disponible."),
                "areas": parsed_response.get("areas", []),
            }

        return parsed_response


class SummaryGeneratorFullText:
    """
    Full-text description generator using Jinja templates.

    Concatenates all researcher information without LLM processing.
    """

    @classmethod
    def generate_researcher_summary(
        cls,
        context: dict,
        prompt_path: Path,
    ) -> str:
        """
        Generate full-text description using Jinja template.

        Args:
            context: Dictionary with 'researcher', 'articles', and 'projects' keys
            prompt_path: Path to the Jinja template file

        Returns:
            Formatted text with all researcher information concatenated
        """
        _, full_prompt = render_prompt(
            system_path=None, prompt_path=prompt_path, context=context
        )

        return full_prompt
