from pydantic import BaseModel, Field
from typing import Optional


class ComputeGraphRequest(BaseModel):
    """
    Request model for computing a researcher graph visualization.

    The graph is computed by retrieving researcher embeddings with the specified
    tag and model, then projecting them to 2D space using the chosen strategy.
    """

    tag: str = Field(
        ...,
        description="Tag identifier for the embeddings (e.g., 'v1_embeddings')",
        examples=["v1_embeddings", "embeddings_v1_avg"],
    )
    model: str = Field(
        ...,
        description="Model identifier used to generate embeddings (e.g., 'gemini-embedding-001')",
        examples=["gemini-embedding-001", "text-embedding-004"],
    )
    strategy: str = Field(
        default="pca",
        description="Dimensionality reduction strategy. Options: 'pca' (direct to 2D), 'umap' (PCA to 50D, then UMAP to 2D), or 'tsne' (PCA to 50D, then t-SNE to 2D)",
        examples=["pca", "umap", "tsne"],
    )
    overwrite: bool = Field(
        default=False,
        description="Whether to overwrite existing graph with the same tag/model combination",
    )


class Node(BaseModel):
    id: str
    label: str
    x: float
    y: float


class Edge(BaseModel):
    source: str
    target: str


class ResearcherNode(Node):
    type: str = "researcher"
    description: Optional[str] = None
    color: str = "#000000"


class ResearcherGraph(BaseModel):
    title: str
    nodes: list[ResearcherNode]
    edges: list[Edge]

    def dump_to_json(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
