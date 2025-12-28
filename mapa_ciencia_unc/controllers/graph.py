import json
import logging

from mapa_ciencia_unc.config import GRAPHS_DIR
from mapa_ciencia_unc.models.graph import ResearcherGraph, ResearcherNode
from mapa_ciencia_unc.models.researcher import Researcher

from sklearn.decomposition import PCA
import umap

logger = logging.getLogger(__name__)


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


def generate_graph_key(tag: str, model: str) -> str:
    """
    Generate a unique key for a graph based on tag and model.

    Args:
        tag: Tag identifier for the embeddings (e.g., "v1_embeddings")
        model: Model identifier used to generate embeddings (e.g., "gemini-embedding-001")

    Returns:
        A string key in the format "{tag}_{model}"
    """
    return f"{tag}_{model}"


def get_available_graphs() -> list[str]:
    """
    Get list of all available pre-computed graph files.

    Scans the GRAPHS_DIR directory for JSON files and returns their names
    without the .json extension.

    Returns:
        List of graph keys (filenames without extension)
    """
    graphs = []
    for graph_file in GRAPHS_DIR.glob("*.json"):
        graphs.append(graph_file.stem)
    return graphs


def get_researcher_graph(graph_key: str | None = None) -> ResearcherGraph:
    """
    Load a pre-computed researcher graph from disk.

    If no graph_key is provided, loads the first available graph.

    Args:
        graph_key: Unique identifier for the graph (tag_model format).
                   If None, uses the first available graph.

    Returns:
        ResearcherGraph object loaded from JSON file

    Raises:
        ValueError: If no graphs are available or if the specified graph_key is not found
    """
    # if no graphs are available, raise an error
    graphs = get_available_graphs()
    if not graphs:
        raise ValueError("No available graphs")

    # if no tag is provided, use the first available graph
    if not graph_key:
        graph_key = graphs[0]

    if graph_key not in graphs:
        raise ValueError(f"Graph {graph_key} not found")

    graph_file_path = GRAPHS_DIR / f"{graph_key}.json"
    with open(graph_file_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

        # Convert the loaded data into Graph model for field validation
        graph = ResearcherGraph(**graph_data)

    return graph


async def get_researcher_embedding(
    tag: str, model: str
) -> tuple[list[Researcher], list[list[float]]]:
    """
    Retrieve researchers and their embedding vectors for a specific tag and model.

    Uses MongoDB aggregation to efficiently filter researchers who have embeddings
    matching the specified tag and model. For each researcher, returns the most
    recently created embedding.

    Args:
        tag: Tag identifier for the embeddings (e.g., "v1_embeddings")
        model: Model identifier used to generate embeddings (e.g., "gemini-embedding-001")

    Returns:
        Tuple containing:
        - List of Researcher objects with matching embeddings
        - List of embedding vectors (each vector is a list of floats)

        Both lists are aligned by index (researchers[i] corresponds to vectors[i])
    """
    pipeline = [
        # 1. First, find the researchers who have at least one matching embedding
        {"$match": {"embeddings": {"$elemMatch": {"tag": tag, "model": model}}}},
        # 2. Redefine the 'embeddings' field to only contain the matches
        {
            "$addFields": {
                "embeddings": {
                    "$filter": {
                        "input": "$embeddings",
                        "as": "emb",
                        "cond": {
                            "$and": [
                                {"$eq": ["$$emb.tag", tag]},
                                {"$eq": ["$$emb.model", model]},
                            ]
                        },
                    }
                }
            }
        },
    ]

    researchers = await Researcher.aggregate(
        pipeline, projection_model=Researcher
    ).to_list()

    # Filter embeddings per researcher and get the most recent one
    vectors = []
    for researcher in researchers:
        embeddings_sorted = sorted(
            researcher.embeddings,
            key=lambda emb: emb.created_at,
            reverse=True,
        )
        latest_embedding = embeddings_sorted[0]
        vectors.append(latest_embedding.vector)

    return researchers, vectors


def _project_with_pca(vectors: list[list[float]]) -> list[tuple[float, float]]:
    """
    Project high-dimensional vectors to 2D using Principal Component Analysis (PCA).

    Args:
        vectors: List of embedding vectors (each vector is a list of floats)

    Returns:
        List of 2D coordinates as (x, y) tuples

    Raises:
        ValueError: If vectors is empty or vectors have inconsistent dimensions
    """
    if not vectors:
        raise ValueError("Cannot project empty vector list")

    pca = PCA(n_components=2)
    emb_2d = pca.fit_transform(vectors)

    # Convert numpy array to list of tuples for easier handling
    return [(float(pos[0]), float(pos[1])) for pos in emb_2d]


def _project_with_umap(vectors: list[list[float]]) -> list[tuple[float, float]]:
    """
    Project high-dimensional vectors to 2D using a two-step process: PCA then UMAP.

    This function uses a two-step dimensionality reduction approach:
    1. PCA to reduce from original dimensions to 50 dimensions
    2. UMAP to reduce from 50 dimensions to 2 dimensions

    This approach is more efficient and often produces better results than
    applying UMAP directly to very high-dimensional data.

    Args:
        vectors: List of embedding vectors (each vector is a list of floats)

    Returns:
        List of 2D coordinates as (x, y) tuples

    Raises:
        ValueError: If vectors is empty or vectors have inconsistent dimensions
    """
    if not vectors:
        raise ValueError("Cannot project empty vector list")

    # Determine the number of components for PCA
    # Use 50 or the number of samples minus 1, whichever is smaller
    n_samples = len(vectors)
    n_features = len(vectors[0])
    pca_components = min(50, n_samples - 1, n_features)

    logger.info(
        f"UMAP projection: Step 1 - PCA from {n_features}D to {pca_components}D"
    )

    # Step 1: Reduce to 50 dimensions with PCA (or fewer if we have fewer samples)
    pca = PCA(n_components=pca_components)
    vectors_pca = pca.fit_transform(vectors)

    logger.info(f"UMAP projection: Step 2 - UMAP from {pca_components}D to 2D")

    # Step 2: Reduce from 50 dimensions to 2 dimensions with UMAP
    reducer = umap.UMAP(
        n_components=2,
        random_state=42,  # For reproducibility
        n_neighbors=15,
        min_dist=0.1,
        metric="euclidean",
    )
    emb_2d = reducer.fit_transform(vectors_pca)

    # Convert numpy array to list of tuples for easier handling
    return [(float(pos[0]), float(pos[1])) for pos in emb_2d]


async def compute_graph(tag: str, model: str, strategy: str = "pca") -> ResearcherGraph:
    """
    Compute a 2D graph visualization of researchers based on their embeddings.

    This function retrieves researcher embeddings, projects them to 2D space using
    the specified strategy, and creates a graph with nodes positioned according to
    the projection. Each node is colored by academic unit.

    Args:
        tag: Tag identifier for the embeddings (e.g., "v1_embeddings")
        model: Model identifier used to generate embeddings (e.g., "gemini-embedding-001")
        strategy: Dimensionality reduction strategy to use (default: "pca")
                  Currently supported: "pca", "umap"
                  - "pca": Principal Component Analysis (direct to 2D)
                  - "umap": Two-step process (PCA to 50D, then UMAP to 2D)

    Returns:
        ResearcherGraph object with nodes positioned in 2D space

    Raises:
        NotImplementedError: If an unsupported strategy is specified
        ValueError: If no researchers have embeddings with the given tag/model

    Note:
        The graph is automatically saved to GRAPHS_DIR as "{tag}_{model}.json"
    """
    # Validate strategy
    strategy_lower = strategy.lower()
    supported_strategies = ["pca", "umap"]
    if strategy_lower not in supported_strategies:
        raise NotImplementedError(
            f"Unsupported strategy: {strategy}. Supported strategies: {', '.join(supported_strategies)}"
        )

    # Get researchers and their embedding vectors
    researchers, vectors = await get_researcher_embedding(tag, model)

    # Project vectors to 2D based on strategy
    logger.info(f"Computing graph for tag: {tag}, model: {model}, strategy: {strategy}")

    if strategy_lower == "pca":
        positions_2d = _project_with_pca(vectors)
    elif strategy_lower == "umap":
        positions_2d = _project_with_umap(vectors)
    else:
        raise NotImplementedError(f"Unsupported strategy: {strategy}")

    # Create nodes from researchers and their 2D positions
    nodes = []
    for researcher, (x, y) in zip(researchers, positions_2d):
        if researcher.research_area:
            description = f"{researcher.research_area} at {researcher.research_center}"
        else:
            description = f"{researcher.research_center}"

        academic_unit = (
            researcher.academic_units[0] if researcher.academic_units else "Otros"
        )
        color = ACADEMIC_UNIT_COLORS.get(academic_unit, ACADEMIC_UNIT_COLORS["Otros"])

        label = f"{researcher.name} ({academic_unit})"

        node = ResearcherNode(
            id=str(researcher.id),
            label=label,
            x=x,
            y=y,
            description=description,
            color=color,
        )

        nodes.append(node)

    # Create graph with no edges (edges can be added in the future)
    edges = []
    graph = ResearcherGraph(
        title=f"Researcher Graph - Summary/Embeddings tag: {tag} and model: {model} ({strategy})",
        nodes=nodes,
        edges=edges,
    )

    # Save graph to disk
    graph_key = generate_graph_key(tag, model)
    output_filename = GRAPHS_DIR / f"{graph_key}.json"
    logging.info(f"Saving graph to file {output_filename}")
    graph.dump_to_json(output_filename)

    return graph
