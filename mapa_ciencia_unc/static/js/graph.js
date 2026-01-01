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

/**
 * Color scheme for academic units
 * Matches the ACADEMIC_UNIT_COLORS from controllers/graph.py
 */
const ACADEMIC_UNIT_COLORS = {
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
};

/**
 * Color scheme for maturity levels
 */
const MATURITY_LEVEL_COLORS = {
  "Exposure": "#42a5f5",
  "Network Building": "#00538A",
  "Project Leadership": "#3B2204",
  // Fallback for unknown levels
  "default": "#9e9e9e",
};

/**
 * Color scheme for ODS (Sustainable Development Goals)
 * Uses the official UN SDG colors
 */
const ODS_COLORS = {
  "Objetivo 1: Fin de la pobreza": "#E5243B",  // No Poverty
  "Objetivo 2: Hambre cero": "#DDA63A",  // Zero Hunger
  "Objetivo 3: Salud y bienestar": "#4C9F38",  // Good Health and Well-being
  "Objetivo 4: Educación de calidad": "#C5192D",  // Quality Education
  "Objetivo 5: Igualdad de género": "#FF3A21",  // Gender Equality
  "Objetivo 6: Agua limpia y saneamiento": "#26BDE2",  // Clean Water and Sanitation
  "Objetivo 7: Energía asequible y no contaminante": "#FCC30B",  // Affordable and Clean Energy
  "Objetivo 8: Trabajo decente y crecimiento económico": "#A21942",  // Decent Work and Economic Growth
  "Objetivo 9: Industria, innovación e infraestructura": "#FD6925",  // Industry, Innovation and Infrastructure
  "Objetivo 10: Reducir las desigualdades entre países y dentro de ellos": "#DD1367", // Reduced Inequalities
  "Objetivo 11: Ciudades": "#FD9D24", // Sustainable Cities and Communities
  "Objetivo 12: Producción y consumo sostenibles": "#BF8B2E", // Responsible Consumption and Production
  "Objetivo 13: Cambio climático": "#3F7E44", // Climate Action
  "Objetivo 14: Océanos": "#0A97D9", // Life Below Water
  "Objetivo 15: Bosques, desertificación y diversidad biológica": "#56C02B", // Life on Land
  "Objetivo 16: Paz y justicia": "#00689D", // Peace, Justice and Strong Institutions
  "Objetivo 17: Alianzas para lograr los ODS": "#19486A", // Partnerships for the Goals
  // Fallback for unknown ODS
  "default": "#9e9e9e",
};

/**
 * Single color scheme (all nodes the same color)
 */
const SINGLE_COLOR = "#3b82f6";

/**
 * Default color for nodes with missing or unknown values
 */
const DEFAULT_COLOR = "#9e9e9e";

/**
 * Maps node properties to a color based on the selected color scheme
 * @param {string} scheme - The color scheme to use ('academic_unit', 'maturity_level', 'ods', 'single')
 * @param {Object} properties - The node properties object
 * @returns {string} The hex color code
 */
function getNodeColor(scheme, properties) {
  if (!properties) {
    return DEFAULT_COLOR;
  }

  switch (scheme) {
    case 'academic_unit': {
      // Academic units is an array, so we'll use the first academic unit for coloring
      const academicUnitsArray = properties.academic_units;
      if (!academicUnitsArray || !Array.isArray(academicUnitsArray) || academicUnitsArray.length === 0) {
        return ACADEMIC_UNIT_COLORS['Otros'];
      }
      const firstAcademicUnit = academicUnitsArray[0];
      return ACADEMIC_UNIT_COLORS[firstAcademicUnit] || ACADEMIC_UNIT_COLORS['Otros'];
    }

    case 'maturity_level': {
      const maturityLevel = properties.maturity_level;
      if (!maturityLevel) return MATURITY_LEVEL_COLORS['default'];
      return MATURITY_LEVEL_COLORS[maturityLevel] || MATURITY_LEVEL_COLORS['default'];
    }

    case 'ods': {
      // ODS is an array, so we'll use the first ODS value for coloring
      const odsArray = properties.ods;
      if (!odsArray || !Array.isArray(odsArray) || odsArray.length === 0) {
        return ODS_COLORS['default'];
      }
      const firstOds = odsArray[0];
      return ODS_COLORS[firstOds] || ODS_COLORS['default'];
    }

    case 'single':
      return SINGLE_COLOR;

    default:
      return DEFAULT_COLOR;
  }
}

/**
 * Get all available color schemes
 * @returns {Array} Array of scheme objects with id and label
 */
function getAvailableColorSchemes() {
  return [
    { id: 'academic_unit', label: 'Unidad Académica Principal' },
    { id: 'maturity_level', label: 'Nivel de Madurez' },
    { id: 'ods', label: 'ODS (Objetivos de Desarrollo Sostenible)' },
    { id: 'single', label: 'Single Color' },
  ];
}

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
    properties: node.properties || {},
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

/**
 * Check if a properties object has any data
 * @param {Object} properties - The properties object to check
 * @returns {boolean} True if properties has data, false otherwise
 */
function hasProperties(properties) {
  return properties && typeof properties === 'object' && Object.keys(properties).length > 0;
}

/**
 * Apply a color scheme to all nodes in the graph
 * Backwards compatible: If a node has no properties, keeps its existing color
 * @param {string} schemeName - The color scheme to apply
 */
function applyColorScheme(schemeName) {
  // Iterate through all nodes and update their color based on the scheme
  graph.forEachNode((nodeId) => {
    const properties = graph.getNodeAttribute(nodeId, 'properties');

    // Backwards compatibility: If node has no properties, keep its existing color
    if (!hasProperties(properties)) {
      // Don't change the color - keep the hardcoded color from old graphs
      return;
    }

    // Calculate and apply new color based on properties
    const newColor = getNodeColor(schemeName, properties);
    graph.setNodeAttribute(nodeId, 'color', newColor);
  });

  // Refresh the renderer to apply the new colors
  renderer.refresh();

  // Store the selected scheme in localStorage for persistence
  try {
    localStorage.setItem('selectedColorScheme', schemeName);
  } catch (error) {
    console.warn('Unable to save color scheme preference', error);
  }
}

/**
 * Get the saved color scheme from localStorage or return default
 * @returns {string} The saved color scheme or 'academic_unit'
 */
function getSavedColorScheme() {
  try {
    return localStorage.getItem('selectedColorScheme') || 'academic_unit';
  } catch (error) {
    console.warn('Unable to retrieve color scheme preference', error);
    return 'academic_unit';
  }
}

// Initialize the color scheme selector
const colorSchemeSelect = document.getElementById('color-scheme-select');
const colorSchemeStatus = document.getElementById('color-scheme-status');

if (colorSchemeSelect) {
  // Set the initial value from localStorage or default
  const savedScheme = getSavedColorScheme();
  colorSchemeSelect.value = savedScheme;

  // Apply the saved color scheme on page load
  applyColorScheme(savedScheme);

  // Add event listener for color scheme changes
  colorSchemeSelect.addEventListener('change', (event) => {
    const selectedScheme = event.target.value;

    if (colorSchemeStatus) {
      colorSchemeStatus.textContent = 'Applying color scheme...';
    }

    // Apply the new color scheme
    applyColorScheme(selectedScheme);

    if (colorSchemeStatus) {
      const schemeLabel = event.target.options[event.target.selectedIndex].text;
      colorSchemeStatus.textContent = `Color scheme "${schemeLabel}" applied.`;
    }
  });
} else {
  console.warn('Color scheme selector not found');
}

