from pydantic import BaseModel, Field
from typing import Optional, Literal
from beanie import Document, PydanticObjectId


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


class ModelTagPair(BaseModel):
    model: str
    tag: str


class ResearcherGraphBase(BaseModel):
    summary: ModelTagPair = Field(
        ...,
        description="Model and tag used to generate the embeddings for this graph",
        examples=[ModelTagPair(model="gemini", tag="summary_v1")],
    )
    embedding: ModelTagPair = Field(
        ...,
        description="Model and tag used for the embeddings in this graph",
        examples=[ModelTagPair(model="gemini-embedding-001", tag="embeddings_v1_avg")],
    )
    strategy: Literal["pca", "umap", "tsne"] = Field(
        ...,
        description="Dimensionality reduction strategy used to compute the graph",
        examples=["pca", "umap", "tsne"],
    )


class ResearcherGraphCreate(ResearcherGraphBase):
    """
    Request model for computing a researcher graph visualization.

    The graph is computed by retrieving researcher embeddings with the specified
    tag and model, then projecting them to 2D space using the chosen strategy.
    """

    overwrite: bool = Field(
        default=False,
        description="Whether to overwrite existing graph with the same tags/models combination",
    )


class ResearcherGraphListItem(ResearcherGraphBase):
    id: PydanticObjectId = Field(alias="_id")
    title: str

    class Config:
        # This allows the model to accept either 'id' or '_id'
        populate_by_name = True


class ResearcherGraph(ResearcherGraphBase, Document):
    title: str
    nodes: list[ResearcherNode]
    edges: list[Edge]

    def dump_to_json(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
