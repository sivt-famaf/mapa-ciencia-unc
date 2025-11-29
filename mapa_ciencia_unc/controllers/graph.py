import json
from pathlib import Path

from mapa_ciencia_unc.models.graph import ResearcherGraph, ResearcherNode, Edge
from mapa_ciencia_unc.models.embedding import Embedding
from mapa_ciencia_unc.models.researcher import Researcher

from sklearn.decomposition import PCA


DATA_DIR = Path(__file__).resolve().parent.parent / "graphs"
DEFAULT_GRAPH_FILE = DATA_DIR / "researcher_graph.json"


def get_researcher_graph(graph_file_path: Path = DEFAULT_GRAPH_FILE) -> ResearcherGraph:
    with open(graph_file_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

        # Convert the loaded data into Graph model for field validation
        graph = ResearcherGraph(**graph_data)

    return graph


async def compute_graph(embeddings_tag: str, strategy: str = "PCA") -> ResearcherGraph:
    # Only PCA is supported for now
    if strategy != "PCA":
        raise NotImplementedError(f"Unsupported strategy: {strategy}")

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

    print(f"Computing graph for {len(researchers)} researchers using {strategy}")
    print(vectors)

    pca = PCA(n_components=2)
    emb_2d = pca.fit_transform(vectors)
    nodes = []
    for researcher, pos in zip(researchers, emb_2d):
        if researcher.research_area:
            description = f"{researcher.research_area} at {researcher.research_center}"
        else:
            description = f"{researcher.research_center}"

        node = ResearcherNode(
            id=str(researcher.id),
            label=researcher.name,
            x=float(pos[0]),
            y=float(pos[1]),
            description=description,
        )

        nodes.append(node)

    edges = []
    graph = ResearcherGraph(
        title=f"Researcher Graph - Embeddings tag: {embeddings_tag}",
        nodes=nodes,
        edges=edges,
    )
    graph.dump_to_json(DEFAULT_GRAPH_FILE)
    return graph
