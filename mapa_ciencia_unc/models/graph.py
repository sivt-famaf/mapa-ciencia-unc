from pydantic import BaseModel
from typing import Optional


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


class ResearcherGraph(BaseModel):
    nodes: list[ResearcherNode]
    edges: list[Edge]
