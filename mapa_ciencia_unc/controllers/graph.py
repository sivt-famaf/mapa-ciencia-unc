import json
from pathlib import Path

from mapa_ciencia_unc.models.graph import ResearcherGraph


DATA_DIR = Path(__file__).resolve().parent.parent / "graphs"


def get_researcher_graph():
    graph_file_path = DATA_DIR / "researcher_graph.json"
    with open(graph_file_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

        # Convert the loaded data into Graph model for field validation
        graph = ResearcherGraph(**graph_data)

    return graph
