import logging

from mapa_ciencia_unc.models.constants import ACADEMIC_UNITS, LANGUAGES, ODS
from mapa_ciencia_unc.models.graph import (
    ResearcherGraph,
    ResearcherNode,
    ResearchTopicNode,
    FilterField,
)
from mapa_ciencia_unc.models.researcher import Researcher
from mapa_ciencia_unc.models.research_topic import ResearchTopic
from mapa_ciencia_unc.models.project import ProjectExtractedIntro
from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.embedding import EmbeddingDocument
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap
import numpy as np

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


async def get_researcher_embedding(
    tag: str, model: str
) -> tuple[list[Researcher], list[list[float]]]:
    """
    Retrieve researchers and their embedding vectors for a specific tag and model.

    Queries the EmbeddingDocument collection to efficiently find embeddings
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
    # Use aggregation to get the most recent embedding per researcher
    pipeline = [
        # Match embeddings with the specified tag and model
        {"$match": {"tag": tag, "model": model}},
        # Sort by created_at descending to get most recent first
        {"$sort": {"created_at": -1}},
        # Group by researcher_id and take the first (most recent) embedding
        {
            "$group": {
                "_id": "$researcher_id",
                "vector": {"$first": "$vector"},
                "created_at": {"$first": "$created_at"},
            }
        },
    ]

    embedding_results = await EmbeddingDocument.aggregate(pipeline).to_list()

    if not embedding_results:
        logger.warning(
            f"No embeddings found for tag='{tag}' and model='{model}'"
        )
        return [], []

    # Extract researcher IDs and vectors
    researcher_ids = [result["_id"] for result in embedding_results]
    vectors = [result["vector"] for result in embedding_results]

    # Fetch corresponding researchers
    researchers = await Researcher.find(
        {"_id": {"$in": researcher_ids}}, fetch_links=False
    ).to_list()

    # Create a mapping from researcher_id to researcher for alignment
    researcher_map = {str(r.id): r for r in researchers}

    # Align researchers and vectors by researcher_id order
    aligned_researchers = []
    aligned_vectors = []

    for researcher_id, vector in zip(researcher_ids, vectors):
        researcher_id_str = str(researcher_id)
        if researcher_id_str in researcher_map:
            aligned_researchers.append(researcher_map[researcher_id_str])
            aligned_vectors.append(vector)
        else:
            logger.warning(
                f"Researcher with id {researcher_id_str} not found, skipping"
            )

    logger.info(
        f"Retrieved {len(aligned_researchers)} researchers with embeddings "
        f"for tag='{tag}' and model='{model}'"
    )

    return aligned_researchers, aligned_vectors


async def get_research_topics_and_mapping(
    tag: str,
) -> tuple[list[ResearchTopic], dict[str, str]]:
    """
    Retrieve research topics and create mapping of researchers to topics.

    Queries ResearchTopic collection for topics matching the specified tag,
    then creates a dictionary mapping each researcher CUIT to their topic name.

    Args:
        tag: Tag identifier for the research topics (e.g., "bertopic-sample15")

    Returns:
        Tuple containing:
        - List of ResearchTopic objects (with embeddings)
        - Dictionary mapping researcher CUIT (str) to topic name (str)

    Example:
        topics, mapping = await get_research_topics_and_mapping("bertopic-sample15")
        # topics: [ResearchTopic(...), ResearchTopic(...), ...]
        # mapping: {"20123456789": "507f1f77bcf86cd799439011", ...}
    """
    # Query research topics matching the tag
    topics = await ResearchTopic.find(ResearchTopic.tag == tag).to_list()

    # Build mapping from CUIT to topic name
    cuit_to_topic_name = {}
    for topic in topics:
        topic_name = str(topic.name)
        for cuit in topic.researcher_cuits:
            cuit_to_topic_name[cuit] = topic_name

    logger.info(
        f"Found {len(topics)} research topics with {len(cuit_to_topic_name)} researcher assignments "
        f"for tag={tag}"
    )

    return topics, cuit_to_topic_name


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
    2. UMAP to reduce from 150 dimensions to 2 dimensions

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
    pca_components = min(150, n_samples - 1, n_features)

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


def _project_with_tsne(vectors: list[list[float]]) -> list[tuple[float, float]]:
    """
    Project high-dimensional vectors to 2D using a two-step process: PCA then t-SNE.

    This function uses a two-step dimensionality reduction approach:
    1. PCA to reduce from original dimensions to 50 dimensions
    2. t-SNE to reduce from 50 dimensions to 2 dimensions

    This approach is more efficient than applying t-SNE directly to very
    high-dimensional data and helps t-SNE focus on meaningful structure.

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
        f"t-SNE projection: Step 1 - PCA from {n_features}D to {pca_components}D"
    )

    # Step 1: Reduce to 50 dimensions with PCA (or fewer if we have fewer samples)
    pca = PCA(n_components=pca_components)
    vectors_pca = pca.fit_transform(vectors)

    logger.info(f"t-SNE projection: Step 2 - t-SNE from {pca_components}D to 2D")

    # Step 2: Reduce from 50 dimensions to 2 dimensions with t-SNE
    tsne = TSNE(
        n_components=2,
        random_state=42,  # For reproducibility
        perplexity=30,  # Balance between local and global structure
        learning_rate=200,  # Standard learning rate
        max_iter=1000,  # Number of iterations
        metric="euclidean",
        init="pca",  # Initialize with PCA for better results
    )
    emb_2d = tsne.fit_transform(vectors_pca)

    # Convert numpy array to list of tuples for easier handling
    return [(float(pos[0]), float(pos[1])) for pos in emb_2d]


async def generate_researcher_metadata(
    researcher: Researcher, cuit_to_topic_name: dict[str, str]
) -> dict:
    """
    Generate metadata for a researcher.
    Used for graph displaying and filtering purposes

    Args:
        researcher: The Researcher object
        cuit_to_topic_name: Mapping from researcher CUIT to research topic name

    Returns:
        Dictionary containing metadata fields for filtering and coloring
    """
    metadata = {}
    metadata["ods"] = researcher.ods
    metadata["languages"] = researcher.languages
    metadata["academic_units"] = researcher.academic_units
    metadata["maturity_level"] = researcher.maturity_level

    # Add research topic assignment if available
    metadata["research_topic"] = cuit_to_topic_name.get(researcher.cuit, "No Topic")

    project_files = await ProjectExtractedIntro.find({"cuit": researcher.cuit}).count()

    articles = await Article.find({"cuit": researcher.cuit}).count()

    amount = project_files + articles
    thresholds = [5, 20]
    multipliers = [1, 1.5, 2]

    # np.digitize returns the index of the bin the amount falls into
    idx = np.digitize(amount, thresholds)
    metadata["size_multiplier"] = multipliers[idx]

    return metadata


async def compute_graph(
    embedding_tag: str,
    embedding_model: str,
    summary_tag: str,
    summary_model: str,
    strategy: str,
    research_topic_tag: str | None = None,
) -> ResearcherGraph:
    """
    Compute a 2D graph visualization of researchers based on their embeddings.

    This function retrieves researcher embeddings, projects them to 2D space using
    the specified strategy, and creates a graph with nodes positioned according to
    the projection. Each node is colored by academic unit.

    Args:
        embedding_tag: Tag identifier for the embeddings (e.g., "v1_embeddings")
        embedding_model: Model identifier used to generate embeddings (e.g., "gemini-embedding-001")
        summary_tag: Tag identifier for the summary (e.g., "v1_summary")
        summary_model: Model identifier used to generate the summary (e.g., "gemini-summary-001")
        strategy: Dimensionality reduction strategy to use (default: "pca")
                  Currently supported: "pca", "umap", "tsne"
                  - "pca": Principal Component Analysis (direct to 2D)
                  - "umap": Two-step process (PCA to 50D, then UMAP to 2D)
                  - "tsne": Two-step process (PCA to 50D, then t-SNE to 2D)
        research_topic_tag: Optional tag identifier for research topics (e.g., "bertopic-sample15")
                           If provided, researchers will be assigned to topics

    Returns:
        ResearcherGraph object with nodes positioned in 2D space

    Raises:
        NotImplementedError: If an unsupported strategy is specified
        ValueError: If no researchers have embeddings with the given tag/model

    Note:
        The graph is automatically stored in the database upon creation.
    """
    # Validate strategy
    strategy_lower = strategy.lower()
    supported_strategies = ["pca", "umap", "tsne"]
    if strategy_lower not in supported_strategies:
        raise NotImplementedError(
            f"Unsupported strategy: {strategy}. Supported strategies: {', '.join(supported_strategies)}"
        )

    # Get researchers and their embedding vectors
    researchers, researcher_vectors = await get_researcher_embedding(
        embedding_tag, embedding_model
    )

    # Get research topic assignments if topic tag is provided
    cuit_to_topic_name = {}
    topics = []
    topic_vectors = []

    if research_topic_tag:
        topics, cuit_to_topic_name = await get_research_topics_and_mapping(
            research_topic_tag
        )
        # Extract topic embedding vectors
        topic_vectors = [topic.embedding.vector for topic in topics]
        logger.info(
            f"Loaded {len(topics)} research topics with embeddings for tag: {research_topic_tag}"
        )

    # Combine researcher and topic vectors for joint projection
    all_vectors = researcher_vectors + topic_vectors
    num_researchers = len(researcher_vectors)
    num_topics = len(topic_vectors)

    # Project all vectors to 2D based on strategy
    logger.info(
        f"Computing graph for embedding_tag: {embedding_tag}, "
        f"embedding_model: {embedding_model}, strategy: {strategy}, "
        f"researchers: {num_researchers}, topics: {num_topics}"
    )

    if strategy_lower == "pca":
        all_positions_2d = _project_with_pca(all_vectors)
    elif strategy_lower == "umap":
        all_positions_2d = _project_with_umap(all_vectors)
    elif strategy_lower == "tsne":
        all_positions_2d = _project_with_tsne(all_vectors)
    else:
        raise NotImplementedError(f"Unsupported strategy: {strategy}")

    # Split projected positions back into researcher and topic positions
    researcher_positions = all_positions_2d[:num_researchers]
    topic_positions = all_positions_2d[num_researchers:]

    # Create researcher nodes from researchers and their 2D positions
    nodes = []
    for researcher, (x, y) in zip(researchers, researcher_positions):
        if researcher.research_area:
            description = f"{researcher.research_area} at {researcher.research_center}"
        else:
            description = f"{researcher.research_center}"

        academic_unit = (
            researcher.academic_units[0] if researcher.academic_units else "Otros"
        )
        metadata = await generate_researcher_metadata(researcher, cuit_to_topic_name)

        label = f"{researcher.name} {researcher.last_name}"
        node = ResearcherNode(
            id=str(researcher.id),
            label=label,
            x=x,
            y=y,
            description=description,
            metadata=metadata,
        )

        nodes.append(node)

    # Create research topic nodes from topics and their 2D positions
    for topic, (x, y) in zip(topics, topic_positions):
        # Count researchers in this topic
        researcher_count = len(topic.researcher_cuits)

        # Create label with topic name in uppercase
        label = topic.name.upper()

        topic_node = ResearchTopicNode(
            id=str(topic.id),
            label=label,
            x=x,
            y=y,
            name=topic.name,
            description=topic.description,
            keywords=topic.keywords,
            researcher_count=researcher_count,
        )

        nodes.append(topic_node)

    logger.info(
        f"Created {len(researcher_positions)} researcher nodes and "
        f"{len(topic_positions)} topic nodes"
    )

    # Create graph with no edges (edges can be added in the future)
    edges = []
    filter_fields = [
        FilterField(key="academic_units", values=list(ACADEMIC_UNITS)),
        FilterField(key="ods", values=ODS),
        FilterField(key="languages", values=LANGUAGES),
    ]

    # Add research topic filter if topics are available
    if research_topic_tag and cuit_to_topic_name:
        # Get unique topic names from the mapping
        unique_topics = sorted(set(cuit_to_topic_name.values()))
        # Add "No Topic" if not all researchers are assigned
        if len(cuit_to_topic_name) < len(researchers):
            unique_topics.append("No Topic")
        filter_fields.append(FilterField(key="research_topic", values=unique_topics))

    graph = ResearcherGraph(
        title=(
            f"Researcher Graph - Summary: {summary_tag}/{summary_model}, "
            f"Embedding: {embedding_tag}/{embedding_model} ({strategy})"
        ),
        nodes=nodes,
        edges=edges,
        embedding={"tag": embedding_tag, "model": embedding_model},
        summary={"tag": summary_tag, "model": summary_model},
        strategy=strategy_lower,
        filter_fields=filter_fields,
    )
    await graph.insert()

    return graph
