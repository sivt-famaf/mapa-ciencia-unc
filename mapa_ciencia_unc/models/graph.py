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
    color: str = "#000000"


class ResearcherGraph(BaseModel):
    title: str
    nodes: list[ResearcherNode]
    edges: list[Edge]

    def dump_to_json(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
