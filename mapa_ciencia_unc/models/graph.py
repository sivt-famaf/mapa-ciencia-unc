from pydantic import BaseModel, Field
from typing import Optional, Literal, List
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
    metadata: dict = Field(
        default_factory=dict,
        description=(
            "Researcher metadata for filtering and coloring. "
            "Expected fields: ods (List[str]), languages (List[str]), "
            "academic_units (List[str]), maturity_level (str), "
            "size_multiplier (float), research_topic (str, optional)"
        )
    )
    color: Optional[str] = Field(
        default="#000000",
        description="Node color (optional for backward compatibility)"
    )


class ResearchTopicNode(Node):
    type: str = "research_topic"
    name: str = Field(description="The research topic name")
    description: Optional[str] = Field(
        default=None,
        description="Description of the research topic"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Keywords associated with this research topic (for hover display)"
    )
    researcher_count: int = Field(
        default=0,
        description="Number of researchers in this topic"
    )


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
    research_topic_tag: Optional[str] = Field(
        default=None,
        description="Optional tag for research topics to assign researchers to topics",
        examples=["bertopic-sample15"],
    )


class ResearcherGraphListItem(ResearcherGraphBase):
    id: PydanticObjectId = Field(alias="_id")
    title: str
    node_count: int = Field(default=0, description="Number of nodes in the graph")

    class Config:
        # This allows the model to accept either 'id' or '_id'
        populate_by_name = True


class FilterField(BaseModel):
    key: str
    values: list[str]


class ResearcherGraph(ResearcherGraphBase, Document):
    title: str
    nodes: list[ResearcherNode | ResearchTopicNode]
    edges: list[Edge]
    filter_fields: list[FilterField] = Field(default_factory=list)

    def dump_to_json(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
