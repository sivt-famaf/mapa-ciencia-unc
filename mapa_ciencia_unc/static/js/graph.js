const modal = document.getElementById("nodeModal");
const modalText = document.getElementById("modalText");
const closeModal = document.getElementById("closeModal");

const openNodeModal = (text) => {
  if (!modal || !modalText) return;
  modalText.textContent = text;
  modal.style.display = "block";
};

const hideModal = () => {
  if (!modal) return;
  modal.style.display = "none";
};

if (closeModal) {
  closeModal.addEventListener("click", hideModal);
}

window.addEventListener("click", (event) => {
  if (event.target === modal) hideModal();
});

const graphDataElement = document.getElementById("graph-data");

if (!graphDataElement) {
  console.error("Unable to find graph data element");
  throw new Error("Missing graph data");
}

let rawData;
try {
  rawData = JSON.parse(graphDataElement.textContent || "{}");
} catch (error) {
  console.error("Unable to parse graph data", error);
  throw error;
}

const numberColors = {
  0: "#e6194b",
  1: "#3cb44b",
  2: "#0082c8",
  3: "#f58231",
  4: "#911eb4",
  5: "#46f0f0",
  6: "#f032e6",
  7: "#d2f53c",
  8: "#fabebe",
  9: "#008080",
};

const Graphology = window.graphology;
const SigmaRenderer = window.Sigma;

if (!Graphology || !SigmaRenderer) {
  console.error("Sigma.js or graphology failed to load");
  throw new Error("Missing graph libraries");
}

const graph = new Graphology.Graph();

rawData.nodes?.forEach((node) => {
  graph.addNode(node.id, {
    label: node.label,
    size: 10,
    color: node.color || "#000000",
    x: node.x,
    y: node.y,
    description: node.description || "",
  });
});

rawData.edges?.forEach((edge) => {
  graph.addEdge(edge.source, edge.target, {
    size: 0,
    color: "#00000000",
  });
});

const container = document.getElementById("container");

if (!container) {
  console.error("Graph container not found");
  throw new Error("Missing graph container");
}

const renderer = new SigmaRenderer(graph, container);

const urlParams = new URLSearchParams(window.location.search);
const currentGraphKey = urlParams.get("graph_key");

const state = {
  hoveredNode: null,
  hoveredNeighbors: new Set(),
  selectedNode: null,
};

renderer.on("enterNode", ({ node }) => {
  if (state.selectedNode) return;
  state.hoveredNode = node;
  state.hoveredNeighbors = new Set(graph.neighbors(node));
  renderer.refresh();
});

renderer.on("leaveNode", () => {
  if (state.selectedNode) return;
  state.hoveredNode = null;
  state.hoveredNeighbors = new Set();
  renderer.refresh();
});

renderer.on("clickNode", ({ node }) => {
  const baseUrl = `/researcher/${encodeURIComponent(node)}`;
  const url = currentGraphKey
    ? `${baseUrl}?graph_key=${encodeURIComponent(currentGraphKey)}`
    : baseUrl;
  window.open(url, "_blank", "noopener");

  if (state.selectedNode === node) {
    state.selectedNode = null;
  } else {
    state.selectedNode = node;
    state.hoveredNode = node;
    state.hoveredNeighbors = new Set(graph.neighbors(node));
  }

  renderer.refresh();
});

renderer.on("clickStage", () => {
  state.selectedNode = null;
  state.hoveredNode = null;
  state.hoveredNeighbors = new Set();
  renderer.refresh();
});

renderer.setSetting("nodeReducer", (node, data) => {
  const res = { ...data };

  if (!state.hoveredNode) {
    return res;
  }

  const isMain = node === state.hoveredNode;
  const isNeighbor = state.hoveredNeighbors.has(node);
  const sameColorAsMain = graph.getNodeAttribute(node, "color") === graph.getNodeAttribute(state.hoveredNode, "color");
  if (sameColorAsMain && !isMain) {
    res.color = graph.getNodeAttribute(node, "color");
  }

  if (!isMain && !isNeighbor && !sameColorAsMain) {
    res.color = "#eee";
    res.forceLabel = false;
    res.labelSize = 0;
  }

  if (isMain) {
    res.size = data.size * 1.5;
    res.forceLabel = true;
  }

  if (isNeighbor || sameColorAsMain) {
    res.size = data.size * 1.2;
    res.forceLabel = true;
  }

  return res;
});

renderer.setSetting("edgeReducer", (edge, data) => {
  if (!state.hoveredNode) {
    return { ...data };
  }

  return { ...data };
});

