import logging
import requests

from pathlib import Path

from mapa_ciencia_unc.llms.utils import render_prompt
from mapa_ciencia_unc.config import OLLAMA_HOST, OLLAMA_API_KEY


logger = logging.getLogger(__name__)


class PortfolioGenerator:
    """Factory class for PortfolioGenerators."""

    @classmethod
    def generate_portfolio(
        cls,
        context: str,
        system_instruction_path: Path,
        prompt_path: Path,
        model_name: str = "gemini-2.5-flash",
    ):
        """
        Generate structured researcher portfolio using LLM models + Jinja templates.

        Args:
            context: Full concatenated information about the researcher.
            system_instruction_path: Path object pointing to the .jinja system instruction file.
            prompt_path: Path object pointing to the .jinja prompt template.
            model_name: Name of the model to use (e.g., "gemini-2.5-flash" or "ollama")

        Returns:
            Dictionary containing the generated portfolio.
        """
        if "gemini" in model_name:
            return PortfolioGeneratorGemini.generate_portfolio(
                context, system_instruction_path, prompt_path, model_name
            )
        elif ("ollama" in model_name) or ("gemma" in model_name):
            return PortfolioGeneratorOllama.generate_portfolio(
                context, prompt_path, model_name
            )
        else:
            raise ValueError(f"Model {model_name} not supported.")


class PortfolioGeneratorGemini:
    """Portfolio generator using Gemini models."""

    @classmethod
    def generate_portfolio(
        cls,
        context: str,
        system_instruction_path: Path,
        prompt_path: Path,
        model_name: str = "gemini-2.5-flash",
    ) -> dict:
        """
        Generate structured researcher portfolio using Gemini models.

        Args:
            context: Full concatenated information about the researcher.
            system_instruction_path: Path object pointing to the .jinja system instruction file.
            prompt_path: Path object pointing to the .jinja prompt template.
            model_name: Name of the Gemini model to use (e.g., "gemini-2.5-flash")

        Returns:
            Dictionary containing the generated portfolio.
        """
        # TODO: Implement portfolio generation logic
        pass


class PortfolioGeneratorOllama:
    """Portfolio generator using Ollama models."""

    @classmethod
    def generate_completion(cls, prompt, model):
        """
        Send request to Ollama API for completion.

        Args:
            prompt: The prompt to send to the model.
            model: The model name to use.

        Returns:
            Response JSON from the Ollama API.
        """
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
        """
        Extract the text response from Ollama API response.

        Args:
            response: JSON response from Ollama API.

        Returns:
            The content text from the response.
        """
        try:
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error("Error in Ollama model output")
            raise e

    @classmethod
    def generate_portfolio(
        cls,
        user_prompt: str,
        researcher_contexts: list[str],
        prompt_path: Path,
        model_name: str = "gemma3:4b",
    ) -> str:
        """
        Generate a portfolio using an Ollama model via remote HTTP API.

        Args:
            user_prompt: The user's instructions for the portfolio.
            researcher_contexts: List of per-researcher context strings
                (as returned by get_portfolio_context).
            prompt_path: Path to the .jinja prompt template.
            model_name: Ollama model identifier.

        Returns:
            The generated portfolio as plain text.
        """
        _, full_prompt = render_prompt(
            system_path=None,
            prompt_path=prompt_path,
            context={
                "user_prompt": user_prompt,
                "researcher_contexts": researcher_contexts,
            },
        )

        response = cls.generate_completion(prompt=full_prompt, model=model_name)
        return cls.extract_response(response)
