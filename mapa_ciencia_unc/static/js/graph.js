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

let renderer;
const filterControlsEl = document.getElementById("filter-controls");
let activeFilterDropdowns = [];
let filterCloserBound = false;
const filterState = { selections: {} };

const formatFilterLabel = (raw) => {
  if (!raw) return "";
  const cleaned = String(raw).replace(/[_-]+/g, " ").trim();
  if (!cleaned) return "";
  return cleaned.replace(/\b\w/g, (c) => c.toUpperCase());
};

const hasActiveFilters = () =>
  Object.values(filterState.selections).some(
    (selected) => selected && selected.size > 0
  );

const nodeMatchesFilters = (node) => {
  if (!hasActiveFilters()) return true;
  const metadata = graph.getNodeAttribute(node, "metadata") || {};

  return Object.entries(filterState.selections).every(([key, selected]) => {
    if (!selected || selected.size === 0) return true;
    const nodeValue = metadata?.[key];
    if (Array.isArray(nodeValue)) {
      return nodeValue.some((entry) => selected.has(String(entry)));
    }
    if (nodeValue === null || nodeValue === undefined) return false;
    return selected.has(String(nodeValue));
  });
};

const renderFilterDropdowns = (filterFields) => {
  if (!filterControlsEl) return;

  activeFilterDropdowns = [];
  filterControlsEl.innerHTML = "";
  filterState.selections = {};

  const closeAll = () => {
    activeFilterDropdowns.forEach((dropdown) =>
      dropdown.classList.remove("open")
    );
  };

  if (!filterCloserBound) {
    document.addEventListener("click", (event) => {
      if (!filterControlsEl.contains(event.target)) {
        closeAll();
      }
    });
    filterCloserBound = true;
  }

  if (!Array.isArray(filterFields) || filterFields.length === 0) {
    const placeholder = document.createElement("span");
    placeholder.className = "filters-empty";
    placeholder.textContent = "No filters available";
    filterControlsEl.appendChild(placeholder);
    return;
  }

  filterFields.forEach((field, fieldIndex) => {
    const filterKey = field?.key ?? `filter_${fieldIndex}`;
    const dropdown = document.createElement("div");
    dropdown.className = "filter-dropdown";

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "filter-toggle";
    const baseLabel = formatFilterLabel(filterKey) || `Filter ${fieldIndex + 1}`;
    toggle.textContent = baseLabel;

    const options = document.createElement("div");
    options.className = "filter-options";

    const values = Array.isArray(field?.values) ? field.values : [];
    const updateSelection = () => {
      const checked = options.querySelectorAll('input[type="checkbox"]:checked');
      const valuesSet = new Set(
        Array.from(checked).map((input) => String(input.value))
      );
      if (valuesSet.size === 0) {
        delete filterState.selections[filterKey];
      } else {
        filterState.selections[filterKey] = valuesSet;
      }

      const checkedCount = valuesSet.size;
      toggle.textContent =
        checkedCount > 0
          ? `${baseLabel} (${checkedCount} selected)`
          : baseLabel;

      if (typeof renderer !== "undefined" && renderer?.refresh) {
        renderer.refresh();
      }
    };

    if (values.length === 0) {
      const empty = document.createElement("div");
      empty.className = "filter-option filters-empty";
      empty.textContent = "No values";
      options.appendChild(empty);
    } else {
      values.forEach((value, valueIndex) => {
        const option = document.createElement("label");
        option.className = "filter-option";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.name = `filter-${filterKey}`;
        checkbox.value = value ?? "";
        checkbox.id = `filter-${filterKey}-${valueIndex}`;

        const text = document.createElement("span");
        text.textContent = value ?? "N/A";

        option.appendChild(checkbox);
        option.appendChild(text);
        options.appendChild(option);

        checkbox.addEventListener("change", updateSelection);
      });
    }

    // initialize label and selection with current state (all unchecked by default)
    updateSelection();

    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const isOpening = !dropdown.classList.contains("open");
      closeAll();
      if (isOpening) {
        dropdown.classList.add("open");
      }
    });

    dropdown.appendChild(toggle);
    dropdown.appendChild(options);
    filterControlsEl.appendChild(dropdown);
    activeFilterDropdowns.push(dropdown);
  });
};

renderFilterDropdowns(rawData?.filter_fields);

const graph = new Graphology.Graph();

rawData.nodes?.forEach((node) => {
  graph.addNode(node.id, {
    label: node.label,
    size: 5 * (node.metadata?.size_multiplier || 1),
    color: node.color || "#000000",
    x: node.x,
    y: node.y,
    description: node.description || "",
    cluster: node.cluster,
    metadata: node.metadata || {},
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

renderer = new SigmaRenderer(graph, container);


const getStoredToken = () => {
  const localToken = localStorage.getItem("jwtToken");
  if (localToken) return localToken;
  const cookieMatch = document.cookie.match(/(?:^|; )token=([^;]+)/);
  return cookieMatch ? decodeURIComponent(cookieMatch[1]) : null;
};

const syncCookieFromStorage = () => {
  const token = localStorage.getItem("jwtToken");
  if (!token) return;
  const maxAgeSeconds = 60 * 60;
  document.cookie = `token=${token}; Path=/; Max-Age=${maxAgeSeconds}; SameSite=Lax`;
};

const ensureToken = () => {
  const token = getStoredToken();
  if (!token) {
    window.location.href = "/login";
    throw new Error("Authentication required");
  }
  return token;
};

// Ensure token exists when landing on graph page
syncCookieFromStorage();
ensureToken();

const urlParams = new URLSearchParams(window.location.search);
const initialGraphId = rawData?._id ?? rawData?.id ?? null;
const currentGraphId = urlParams.get("graph_id") || initialGraphId;

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
  const url = currentGraphId
    ? `${baseUrl}?graph_id=${encodeURIComponent(currentGraphId)}`
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

  const passesFilters = nodeMatchesFilters(node);
  if (!passesFilters) {
    res.color = "#eee";
    res.forceLabel = false;
    res.labelSize = 0;
    return res;
  }

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

