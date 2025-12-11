import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from mapa_ciencia_unc.models.graph import ResearcherGraph, ResearcherNode, Edge
from mapa_ciencia_unc.models.embedding import Embedding
from mapa_ciencia_unc.models.researcher import Researcher

from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

from pydantic import BaseModel


DATA_DIR = Path(__file__).resolve().parent.parent / "graphs"

ACADEMIC_UNIT_COLORS = {
    "FP": "#FFB300",
    "FCM": "#803E75",
    "FCQ": "#FF6800",
    "FA": "#A6BDD7",
    "FaMAF": "#C10020",
    "FO": "#CEA262",
    "FL": "#817066",
    "FCE": "#007D34",
    "FAUD": "#F6768E",
    "FFyH": "#00538A",
    "FCEFyN": "#FF7A5C",
    "FCS": "#FF8E00",
    "FCA": "#3B2204",
    "FCC": "#F4C800",
    "Otros": "#53377A",
}


class GraphCard(BaseModel):
    """Metadata for a graph embedding."""
    dataset_id: str
    method: str  # 'pca' or 'tsne'
    tag: str  # embeddings tag
    original_dimension: int
    target_dimension: int = 2
    timestamp: str
    n_samples: int
    parameters: Optional[dict] = None  # Additional method-specific parameters


def get_available_graphs() -> list[str]:
    """Get list of available graph dataset IDs.

    Returns list of directory names under DATA_DIR/graphs/
    Each directory represents a graph dataset.
    """
    graphs = []
    if not DATA_DIR.exists():
        return graphs

    for graph_dir in DATA_DIR.iterdir():
        if graph_dir.is_dir() and (graph_dir / "graph.json").exists():
            graphs.append(graph_dir.name)
    return graphs


def get_graph_metadata(tag: str) -> GraphCard:
    """Load graph metadata (graph_card.json) for a dataset.

    Args:
        tag: The dataset ID (directory name).

    Returns:
        GraphCard object with metadata.

    Raises:
        ValueError: If metadata file doesn't exist.
    """
    graph_dir = DATA_DIR / tag
    metadata_file = graph_dir / "graph_card.json"

    if not metadata_file.exists():
        raise ValueError(f"Metadata file not found for tag: {tag}")

    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        return GraphCard(**metadata)


def get_researcher_graph(tag: str | None = None) -> ResearcherGraph:
    """Load a researcher graph by dataset ID.

    Args:
        tag: The dataset ID (directory name). If None, uses the first available graph.

    Returns:
        ResearcherGraph object with nodes and edges.

    Raises:
        ValueError: If no graphs are available or tag doesn't exist.
    """
    # if no graphs are available, raise an error
    tag_list = get_available_graphs()
    if not tag_list:
        raise ValueError("No available graphs")

    # if no tag is provided, use the first available graph
    if not tag:
        tag = tag_list[0]

    # Load from new directory structure
    graph_dir = DATA_DIR / tag
    graph_file_path = graph_dir / "graph.json"

    if not graph_file_path.exists():
        raise ValueError(f"Graph file not found for tag: {tag}")

    with open(graph_file_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

        # Convert the loaded data into Graph model for field validation
        graph = ResearcherGraph(**graph_data)

    return graph


async def compute_graph(embeddings_tag: str, method: str = "pca") -> ResearcherGraph:
    # Validate method parameter
    method_lower = method.lower()
    if method_lower not in ["pca", "tsne"]:
        raise ValueError(
            f"Unsupported method: {method}. Supported methods: 'pca', 'tsne'"
        )

    researchers = await Researcher.find(
        {"embeddings": {"$elemMatch": {"tag": embeddings_tag}}}
    ).to_list()

    vectors = []
    # 2. Filter embeddings per researcher
    for r in researchers:
        filtered_embs = [e for e in r.embeddings if e.tag == embeddings_tag]
        emb = sorted(
            filtered_embs,
            key=lambda e: e.created_at,
            reverse=True,
        )[0]
        vectors.append(emb.vector)

    original_dimension = len(vectors[0]) if vectors else 0

    # Store method-specific parameters
    method_params = {}

    # Apply dimensionality reduction based on method
    if method_lower == "pca":
        reducer = PCA(n_components=2)
        emb_2d = reducer.fit_transform(vectors)
    elif method_lower == "tsne":  # tsne
        # First reduce to dimension 30 and then apply tsne
        reducer = PCA(n_components=30)
        emb_30d = reducer.fit_transform(vectors)
        perplexity = min(30, len(emb_30d) - 1)
        method_params = {
            "perplexity": perplexity,
            "random_state": 42,
            "max_iter": 500,
            "intermediate_pca_dimension": 30
        }
        reducer = TSNE(
            n_components=2,
            random_state=42,
            perplexity=perplexity,  # Ensure perplexity < n_samples
            max_iter=500,
        )
        emb_2d = reducer.fit_transform(emb_30d)
    else:
        raise ValueError(
            f"Incorrect method to reduce embedding dimensioanility {method_lower}"
        )

    nodes = []
    for researcher, pos in zip(researchers, emb_2d):
        if researcher.research_area:
            description = f"{researcher.research_area} at {researcher.research_center}"
        else:
            description = f"{researcher.research_center}"

        academic_unit = (
            researcher.academic_units[0] if researcher.academic_units else "Otros"
        )
        color = ACADEMIC_UNIT_COLORS.get(academic_unit, ACADEMIC_UNIT_COLORS["Otros"])

        label = f"{researcher.name} {researcher.last_name} ({academic_unit})"

        node = ResearcherNode(
            id=str(researcher.id),
            label=label,
            x=float(pos[0]),
            y=float(pos[1]),
            description=description,
            color=color,
        )

        nodes.append(node)

    edges = []
    graph = ResearcherGraph(
        title=f"Researcher Graph - Summary/Embeddings tag: {embeddings_tag}",
        nodes=nodes,
        edges=edges,
    )

    # Create dataset ID and directory structure
    dataset_id = f"{embeddings_tag}_{method_lower}"
    graph_dir = DATA_DIR / dataset_id
    graph_dir.mkdir(parents=True, exist_ok=True)

    # Save graph data (embeddings)
    graph_file = graph_dir / "graph.json"
    graph.dump_to_json(str(graph_file))

    # Create and save graph card metadata
    graph_card = GraphCard(
        dataset_id=dataset_id,
        method=method_lower,
        tag=embeddings_tag,
        original_dimension=original_dimension,
        target_dimension=2,
        timestamp=datetime.now().isoformat(),
        n_samples=len(researchers),
        parameters=method_params if method_params else None
    )

    graph_card_file = graph_dir / "graph_card.json"
    with open(graph_card_file, "w", encoding="utf-8") as f:
        f.write(graph_card.model_dump_json(indent=2))

    return graph
