import logging
import requests

from pathlib import Path

from google import genai
from google.genai import types

from mapa_ciencia_unc.llms.utils import render_prompt
from mapa_ciencia_unc.config import GEMINI_API_KEY, OLLAMA_HOST, OLLAMA_API_KEY


logger = logging.getLogger(__name__)


class PortfolioGenerator:
    """Factory class for PortfolioGenerators."""

    @classmethod
    def generate_portfolio(
        cls,
        user_prompt: str,
        researcher_contexts: list[str],
        prompt_path: Path,
        model_name: str = "gemini-2.5-flash",
    ) -> str:
        """
        Generate a portfolio using the appropriate backend based on model_name.

        Args:
            user_prompt: The user's instructions for the portfolio.
            researcher_contexts: List of per-researcher context strings.
            prompt_path: Path to the .jinja prompt template.
            model_name: Name of the model to use (e.g., "gemini-2.5-flash", "gemma3:27b")

        Returns:
            The generated portfolio as plain text.
        """
        if "gemini" in model_name:
            return PortfolioGeneratorGemini.generate_portfolio(
                user_prompt, researcher_contexts, prompt_path, model_name
            )
        else:
            return PortfolioGeneratorOllama.generate_portfolio(
                user_prompt, researcher_contexts, prompt_path, model_name
            )


class PortfolioGeneratorGemini:
    """Portfolio generator using Gemini models."""

    @classmethod
    def generate_portfolio(
        cls,
        user_prompt: str,
        researcher_contexts: list[str],
        prompt_path: Path,
        model_name: str = "gemini-2.5-flash",
    ) -> str:
        """
        Generate a portfolio using a Gemini model.

        Args:
            user_prompt: The user's instructions for the portfolio.
            researcher_contexts: List of per-researcher context strings.
            prompt_path: Path to the .jinja prompt template.
            model_name: Name of the Gemini model to use (e.g., "gemini-2.5-flash")

        Returns:
            The generated portfolio as plain text.
        """
        _, prompt = render_prompt(
            system_path=None,
            prompt_path=prompt_path,
            context={
                "user_prompt": user_prompt,
                "researcher_contexts": researcher_contexts,
            },
        )

        client = genai.Client(api_key=GEMINI_API_KEY)
        config = types.GenerateContentConfig(temperature=0.7)

        logger.info(f"Sending request to Gemini API with model {model_name}...")
        response = client.models.generate_content(
            model=model_name, contents=prompt, config=config
        )
        return response.text


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
