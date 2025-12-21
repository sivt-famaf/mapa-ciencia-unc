from typing import List
from google import genai
from google.genai import types

from mapa_ciencia_unc.config import GEMINI_API_KEY

def generate_gemini_embedding(
    profile_summary: str,
    output_dim: int = 768
) -> List[float]:
    """
    Generate a semantic embedding using the Gemini model 'gemini-embedding-001'
    and reduce its dimensionality using PCA.

    Args:
        profile_summary : Researcher's summarized profile. It must be a single textual description
        containing background, expertise, and scientific contributions.
        output_dim : Target dimensionality for PCA reduction. Default is 768.

    Returns:
        List with a single embedding vector with reduced dimensionality.
    """

    try:
        client = genai.Client(api_key = GEMINI_API_KEY)

        config = types.EmbedContentConfig(
            output_dimensionality=output_dim
        )

        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=profile_summary,
            config=config
        )

        return response.embeddings[0].values

    except Exception as e:
        print(f"Error generating the embedding: {e}")
        return []