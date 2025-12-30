import logging
import requests
from typing import List

from google import genai
from google.genai import types

from mapa_ciencia_unc.config import GEMINI_API_KEY, OLLAMA_HOST, OLLAMA_API_KEY

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Factory class for EmbeddingGenerators.

    Routes embedding generation requests to the appropriate implementation based
    on the model name. Supports multiple embedding providers (Gemini, Ollama).
    """

    @classmethod
    def generate_embedding(
        cls,
        text: str,
        model_name: str = "gemini-embedding-001",
        output_dim: int = 512,
    ) -> List[float]:
        """
        Generate a semantic embedding vector for the given text using specified model.

        This method acts as a router, delegating to the appropriate embedding generator
        implementation based on the model name.

        Args:
            text: Text content to embed (e.g., researcher profile, summary, abstract)
            model_name: Name of the embedding model to use
                - "gemini-embedding-001" or similar for Gemini models
                - "ollama" or model names containing "ollama", "nomic" or "qwen"
            output_dim: Target dimensionality for the embedding vector (default: 768)

        Returns:
            List of floats representing the embedding vector.
            Returns empty list on error.

        Raises:
            ValueError: If the model name is not supported
        """
        if "gemini" in model_name:
            return EmbeddingGeneratorGemini.generate_embedding(
                text=text,
                model_name=model_name,
                output_dim=output_dim,
            )
        elif (
            ("ollama" in model_name)
            or ("nomic" in model_name)
            or ("qwen" in model_name)
        ):
            return EmbeddingGeneratorOllama.generate_embedding(
                text=text,
                model_name=model_name,
                output_dim=output_dim,
            )
        else:
            raise ValueError(
                f"Model '{model_name}' not supported. "
                "Supported models: Gemini models (containing 'gemini'), "
                "Ollama models (containing 'ollama', 'nomic' or 'qwen')"
            )


class EmbeddingGeneratorGemini:
    """
    Gemini-based embedding generator implementation.

    Uses Google's Gemini API to generate high-quality semantic embeddings
    with configurable output dimensionality.
    """

    @classmethod
    def generate_embedding(
        cls,
        text: str,
        model_name: str = "gemini-embedding-001",
        output_dim: int = 768,
    ) -> List[float]:
        """
        Generate a semantic embedding using Google's Gemini embedding models.

        Uses the Gemini API to create dense vector representations of text that
        capture semantic meaning. The embeddings can be used for similarity search,
        clustering, and other NLP tasks.

        Args:
            text: Text content to embed. Should be a coherent piece of text
                  (e.g., researcher profile, paper abstract, summary).
                  Works best with text between 10-2000 words.
            model_name: Gemini model identifier (default: "gemini-embedding-001")
            output_dim: Target dimensionality for the embedding vector.

        Returns:
            List of floats representing the embedding vector with length=output_dim.
            Returns empty list if an error occurs during generation.

        Raises:
            ValueError: If GEMINI_API_KEY is not configured in environment

        Notes:
            - Requires GEMINI_API_KEY to be set in .env file
            - The embedding is L2-normalized by the API
        """
        if not GEMINI_API_KEY:
            raise ValueError(
                "Variable GEMINI_API_KEY not set. Provide a value in .env file"
            )

        client = genai.Client(api_key=GEMINI_API_KEY)
        config = types.EmbedContentConfig(output_dimensionality=output_dim)

        response = client.models.embed_content(
            model=model_name,
            contents=text,
            config=config,
        )

        return response.embeddings[0].values


class EmbeddingGeneratorOllama:
    """
    Ollama-based embedding generator using remote HTTP API.
    """

    @classmethod
    def generate_embedding(
        cls,
        text: str,
        model_name: str = "nomic-embed-text:latest",
        output_dim: int = 768,  # Unused
    ) -> List[float]:
        """
        Generate embedding using Ollama models via HTTP API.

        Args:
            text: Text to embed
            model_name: Ollama model (e.g., "nomic-embed-text:latest",
                "qwen3-embedding:8b")
            output_dim: Not used (Ollama models have fixed dimensions)

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If OLLAMA_HOST or OLLAMA_API_KEY not set
            requests.HTTPError: If API request fails
        """
        if not OLLAMA_HOST:
            raise ValueError("OLLAMA_HOST not set in .env file")
        if not OLLAMA_API_KEY:
            raise ValueError("OLLAMA_API_KEY not set in .env file")

        url = f"{OLLAMA_HOST}/api/embeddings"
        headers = {
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": model_name,
            "input": text,
        }

        logger.info(f"Requesting Ollama embedding: model={model_name}")
        response = requests.post(url, headers=headers, json=data, timeout=120)
        import ipdb; ipdb.set_trace()
        if (
            response.status_code == 500
            and "length exceeds" in str(response.content)
        ):
            raise ValueError(
                "Input length exceeds the context length "
                "({} words approx.)".format(len(text.split(" ")))
            )
        response.raise_for_status()

        result = response.json()

        # Extract embedding from response
        # Format: {"data": [{"embedding": [....]} ]}
        try:
            return result["data"][0]["embedding"]
        except Exception:
            raise ValueError(f"Unexpected response format: {result}")
