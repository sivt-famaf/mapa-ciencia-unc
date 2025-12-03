import json
from pathlib import Path

from mapa_ciencia_unc.models.graph import ResearcherGraph, ResearcherNode, Edge
from mapa_ciencia_unc.models.embedding import Embedding
from mapa_ciencia_unc.models.researcher import Researcher

from sklearn.decomposition import PCA


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


def get_available_graphs() -> list[str]:
    graphs = []
    for graph_file in DATA_DIR.glob("*.json"):
        graphs.append(graph_file.stem)
    return graphs


def get_researcher_graph(tag: str | None = None) -> ResearcherGraph:
    # if no graphs are available, raise an error
    tag_list = get_available_graphs()
    if not tag_list:
        raise ValueError("No available graphs")

    # if no tag is provided, use the first available graph
    if not tag:
        tag = tag_list[0]

    graph_file_path = DATA_DIR / f"{tag}.json"
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

        academic_unit = (
            researcher.academic_units[0] if researcher.academic_units else "Otros"
        )
        color = ACADEMIC_UNIT_COLORS.get(academic_unit, ACADEMIC_UNIT_COLORS["Otros"])

        label = f"{researcher.name} ({academic_unit})"

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
    graph.dump_to_json(DATA_DIR / f"{embeddings_tag}.json")
    return graph
