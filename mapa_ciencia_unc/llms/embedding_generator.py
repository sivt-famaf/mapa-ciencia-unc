import logging
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
        output_dim: int = 768,
    ) -> List[float]:
        """
        Generate a semantic embedding vector for the given text using specified model.

        This method acts as a router, delegating to the appropriate embedding generator
        implementation based on the model name.

        Args:
            text: Text content to embed (e.g., researcher profile, summary, abstract)
            model_name: Name of the embedding model to use
                        - "gemini-embedding-001" or similar for Gemini models
                        - "ollama" or model names containing "ollama" for Ollama models
            output_dim: Target dimensionality for the embedding vector (default: 768)

        Returns:
            List of floats representing the embedding vector.
            Returns empty list on error.

        Raises:
            ValueError: If the model name is not supported

        Examples:
            >>> embedding = EmbeddingGenerator.generate_embedding(
            ...     text="Researcher specializing in machine learning",
            ...     model_name="gemini-embedding-001",
            ...     output_dim=768
            ... )
            >>> len(embedding)
            768
        """
        if "gemini" in model_name:
            return EmbeddingGeneratorGemini.generate_embedding(
                text=text,
                model_name=model_name,
                output_dim=output_dim,
            )
        elif "ollama" in model_name:
            return EmbeddingGeneratorOllama.generate_embedding(
                text=text,
                model_name=model_name,
                output_dim=output_dim,
            )
        else:
            raise ValueError(
                f"Model '{model_name}' not supported. "
                "Supported models: Gemini models (containing 'gemini'), "
                "Ollama models (containing 'ollama')"
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
                        - "gemini-embedding-001": Standard embedding model (768D default)
                        - "text-embedding-004": Latest embedding model
            output_dim: Target dimensionality for the embedding vector.
                        Supported values depend on the model (typically up to 768).
                        Lower dimensions may lose some information but are faster.

        Returns:
            List of floats representing the embedding vector with length=output_dim.
            Returns empty list if an error occurs during generation.

        Raises:
            ValueError: If GEMINI_API_KEY is not configured in environment

        Notes:
            - Requires GEMINI_API_KEY to be set in .env file
            - The embedding is L2-normalized by the API
            - Embedding generation typically takes 100-500ms
            - Maximum input text length varies by model (typically 2048 tokens)

        Examples:
            >>> embeddings = EmbeddingGeneratorGemini.generate_embedding(
            ...     text="Machine learning researcher with focus on NLP",
            ...     model_name="gemini-embedding-001",
            ...     output_dim=512
            ... )
            >>> len(embeddings)
            512
        """
        if not GEMINI_API_KEY:
            raise ValueError(
                "Variable GEMINI_API_KEY not set. Provide a value in .env file"
            )

        client = genai.Client(api_key=GEMINI_API_KEY)
        config = types.EmbedContentConfig(output_dimensionality=output_dim)

        try:
            response = client.models.embed_content(
                model=model_name,
                contents=text,
                config=config,
            )

            return response.embeddings[0].values

        except Exception as e:
            logger.error(f"Error generating embedding with Gemini: {e}")
            return []


class EmbeddingGeneratorOllama:
    """
    Ollama-based embedding generator implementation (placeholder).

    This class is a placeholder for future implementation of Ollama-based
    embedding generation via remote HTTP API.

    Note:
        This implementation will be completed in the future. For now, it raises
        NotImplementedError when called.
    """

    @classmethod
    def generate_embedding(
        cls,
        text: str,
        model_name: str = "nomic-embed-text",
        output_dim: int = 768,
    ) -> List[float]:
        """
        Generate a semantic embedding using Ollama embedding models (NOT IMPLEMENTED).

        This method is a placeholder for future implementation of Ollama-based
        embedding generation.

        Args:
            text: Text content to embed
            model_name: Ollama model identifier (e.g., "nomic-embed-text", "mxbai-embed-large")
            output_dim: Target dimensionality for the embedding vector

        Returns:
            List of floats representing the embedding vector

        Raises:
            NotImplementedError: This method is not yet implemented

        Future Implementation:
            - Will connect to OLLAMA_HOST via HTTP API
            - Will support various Ollama embedding models
            - Will use OLLAMA_API_KEY for authentication
            - Will implement similar error handling as Gemini implementation
        """
        raise NotImplementedError(
            "EmbeddingGeneratorOllama is not yet implemented. "
            "This will be added in a future update to support Ollama-based embeddings."
        )


# Backward compatibility: Keep the original function name as an alias
def generate_gemini_embedding(
    profile_summary: str,
    output_dim: int = 768,
) -> List[float]:
    """
    Generate a semantic embedding using the Gemini model (backward compatibility).

    This function is maintained for backward compatibility. New code should use
    EmbeddingGenerator.generate_embedding() or EmbeddingGeneratorGemini.generate_embedding().

    Args:
        profile_summary: Researcher's summarized profile or any text to embed
        output_dim: Target dimensionality for the embedding (default: 768)

    Returns:
        List of floats representing the embedding vector

    See Also:
        EmbeddingGenerator.generate_embedding(): New recommended interface
        EmbeddingGeneratorGemini.generate_embedding(): Direct Gemini implementation
    """
    return EmbeddingGeneratorGemini.generate_embedding(
        text=profile_summary,
        model_name="gemini-embedding-001",
        output_dim=output_dim,
    )