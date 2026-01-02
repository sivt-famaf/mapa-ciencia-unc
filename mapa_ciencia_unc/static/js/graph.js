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
 * Maps node metadata to a color based on the selected color scheme
 * @param {string} scheme - The color scheme to use ('academic_unit', 'maturity_level', 'ods', 'single')
 * @param {Object} metadata - The node metadata object
 * @returns {string} The hex color code
 */
function getNodeColor(scheme, metadata) {
  if (!metadata) {
    return DEFAULT_COLOR;
  }

  switch (scheme) {
    case 'academic_unit': {
      // Academic units is an array, so we'll use the first academic unit for coloring
      const academicUnitsArray = metadata.academic_units;
      if (!academicUnitsArray || !Array.isArray(academicUnitsArray) || academicUnitsArray.length === 0) {
        return ACADEMIC_UNIT_COLORS['Otros'];
      }
      const firstAcademicUnit = academicUnitsArray[0];
      return ACADEMIC_UNIT_COLORS[firstAcademicUnit] || ACADEMIC_UNIT_COLORS['Otros'];
    }

    case 'maturity_level': {
      const maturityLevel = metadata.maturity_level;
      if (!maturityLevel) return MATURITY_LEVEL_COLORS['default'];
      return MATURITY_LEVEL_COLORS[maturityLevel] || MATURITY_LEVEL_COLORS['default'];
    }

    case 'ods': {
      // ODS is an array, so we'll use the first ODS value for coloring
      const odsArray = metadata.ods;
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
    metadata: node.metadata || {},
  });
});

rawData.edges?.forEach((edge) => {
  graph.addEdge(edge.source, edge.target, {
    size: 0,
    color: "#00000000",
  });
});

/**
 * Check if the graph has metadata (new graphs) or hardcoded colors (old graphs)
 * @returns {boolean} True if graph has metadata and supports color schemes
 */
function graphSupportsColorSchemes() {
  let nodesWithMetadata = 0;
  let totalNodes = 0;

  graph.forEachNode((nodeId) => {
    totalNodes++;
    const metadata = graph.getNodeAttribute(nodeId, 'metadata');
    if (hasMetadata(metadata)) {
      nodesWithMetadata++;
    }
  });

  // If at least 50% of nodes have metadata, we support color schemes
  return totalNodes > 0 && (nodesWithMetadata / totalNodes) >= 0.5;
}

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

/**
 * Check if a metadata object has any data
 * @param {Object} metadata - The metadata object to check
 * @returns {boolean} True if metadata has data, false otherwise
 */
function hasMetadata(metadata) {
  return metadata && typeof metadata === 'object' && Object.keys(metadata).length > 0;
}

/**
 * Apply a color scheme to all nodes in the graph
 * Backwards compatible: If a node has no metadata, keeps its existing color
 * @param {string} schemeName - The color scheme to apply
 */
function applyColorScheme(schemeName) {
  // Iterate through all nodes and update their color based on the scheme
  graph.forEachNode((nodeId) => {
    const metadata = graph.getNodeAttribute(nodeId, 'metadata');

    // Backwards compatibility: If node has no metadata, keep its existing color
    if (!hasMetadata(metadata)) {
      // Don't change the color - keep the hardcoded color from old graphs
      return;
    }

    // Calculate and apply new color based on metadata
    const newColor = getNodeColor(schemeName, metadata);
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

/**
 * Get the saved legend collapsed state from localStorage
 * @returns {boolean} True if legend should be collapsed
 */
function getLegendCollapsedState() {
  try {
    const collapsed = localStorage.getItem('legendCollapsed');
    return collapsed === 'true';
  } catch (error) {
    console.warn('Unable to retrieve legend collapsed state', error);
    return true; // Default to collapsed
  }
}

/**
 * Save the legend collapsed state to localStorage
 * @param {boolean} collapsed - Whether the legend is collapsed
 */
function saveLegendCollapsedState(collapsed) {
  try {
    localStorage.setItem('legendCollapsed', collapsed.toString());
  } catch (error) {
    console.warn('Unable to save legend collapsed state', error);
  }
}

/**
 * Render the color legend based on the current color scheme
 * @param {string} schemeName - The color scheme to show in the legend
 */
function renderLegend(schemeName) {
  const legendEl = document.getElementById('color-legend');
  if (!legendEl) return;

  // Check if this is the first render (legend is empty)
  const isFirstRender = legendEl.innerHTML === '';

  // Check if legend was previously collapsed
  const wasCollapsed = legendEl.classList.contains('collapsed');
  const savedCollapsed = getLegendCollapsedState();

  // Clear existing legend
  legendEl.innerHTML = '';

  let colorMap = {};
  let title = '';

  // Build the color map and title based on the scheme
  switch (schemeName) {
    case 'academic_unit':
      colorMap = ACADEMIC_UNIT_COLORS;
      title = 'Academic Unit';
      break;
    case 'maturity_level':
      colorMap = MATURITY_LEVEL_COLORS;
      title = 'Maturity Level';
      break;
    case 'ods':
      colorMap = ODS_COLORS;
      title = 'ODS';
      break;
    case 'single':
      // For single color, show just one item
      colorMap = { 'All Nodes': SINGLE_COLOR };
      title = 'Color Scheme';
      break;
    default:
      // If unknown scheme, don't show legend
      return;
  }

  // Create header with title and toggle button
  const headerEl = document.createElement('div');
  headerEl.className = 'color-legend-header';

  const titleEl = document.createElement('div');
  titleEl.className = 'color-legend-title';
  titleEl.textContent = title;

  const toggleBtn = document.createElement('button');
  toggleBtn.className = 'color-legend-toggle';
  toggleBtn.innerHTML = '▼';
  toggleBtn.setAttribute('aria-label', 'Toggle legend');

  headerEl.appendChild(titleEl);
  headerEl.appendChild(toggleBtn);
  legendEl.appendChild(headerEl);

  // Create content wrapper
  const contentEl = document.createElement('div');
  contentEl.className = 'color-legend-content';

  // Create legend items
  Object.entries(colorMap).forEach(([label, color]) => {
    // Skip 'default' entries
    if (label === 'default') return;

    const itemEl = document.createElement('div');
    itemEl.className = 'color-legend-item';

    const swatchEl = document.createElement('div');
    swatchEl.className = 'color-legend-swatch';
    swatchEl.style.backgroundColor = color;

    const labelEl = document.createElement('div');
    labelEl.className = 'color-legend-label';
    labelEl.textContent = label;

    itemEl.appendChild(swatchEl);
    itemEl.appendChild(labelEl);
    contentEl.appendChild(itemEl);
  });

  legendEl.appendChild(contentEl);

  // Apply collapsed state
  // On first render, use saved state (defaults to true/collapsed)
  // On re-render (color scheme change), maintain current collapsed state
  const shouldBeCollapsed = isFirstRender ? savedCollapsed : wasCollapsed;
  if (shouldBeCollapsed) {
    legendEl.classList.add('collapsed');
  }

  // Add toggle functionality
  headerEl.addEventListener('click', () => {
    const isCollapsed = legendEl.classList.toggle('collapsed');
    saveLegendCollapsedState(isCollapsed);
  });
}

// Check if graph supports color schemes (has metadata)
const supportsColorSchemes = graphSupportsColorSchemes();

// Hide color scheme controls and legend if graph doesn't support color schemes
const colorSchemeControlsEl = document.getElementById('color-scheme-controls');
const colorLegendEl = document.getElementById('color-legend');

if (!supportsColorSchemes) {
  if (colorSchemeControlsEl) {
    colorSchemeControlsEl.style.display = 'none';
  }
  if (colorLegendEl) {
    colorLegendEl.style.display = 'none';
  }
}

// Initialize the color scheme selector (only if supported)
const colorSchemeDropdown = document.getElementById('color-scheme-select');
const colorSchemeStatus = document.getElementById('color-scheme-status');

if (colorSchemeDropdown && supportsColorSchemes) {
  const toggleEl = colorSchemeDropdown.querySelector('.custom-dropdown-toggle');
  const optionsEl = colorSchemeDropdown.querySelector('.custom-dropdown-options');

  if (toggleEl && optionsEl) {
    // Color scheme options mapping
    const schemeOptions = {
      'academic_unit': 'Academic Unit',
      'maturity_level': 'Maturity Level',
      'ods': 'ODS (Sustainable Development Goals)',
      'single': 'Single Color'
    };

    // Set the initial value from localStorage or default
    const savedScheme = getSavedColorScheme();

    // Update the toggle button text to show current selection
    const textEl = toggleEl.querySelector('.custom-dropdown-toggle-text');
    if (textEl) {
      textEl.textContent = schemeOptions[savedScheme] || schemeOptions['academic_unit'];
    }

    // Apply the saved color scheme on page load
    applyColorScheme(savedScheme);
    renderLegend(savedScheme);

    // Mark the current selection
    const currentOption = optionsEl.querySelector(`[data-value="${savedScheme}"]`);
    if (currentOption) {
      currentOption.classList.add('selected');
    }

    // Close all custom dropdowns helper
    const closeAllCustomDropdowns = () => {
      document.querySelectorAll('.custom-dropdown.open').forEach(dropdown => {
        if (dropdown !== colorSchemeDropdown) {
          dropdown.classList.remove('open');
        }
      });
    };

    // Toggle dropdown open/close
    toggleEl.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const wasOpen = colorSchemeDropdown.classList.contains('open');
      closeAllCustomDropdowns();
      if (!wasOpen) {
        colorSchemeDropdown.classList.add('open');
      } else {
        colorSchemeDropdown.classList.remove('open');
      }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (event) => {
      if (!colorSchemeDropdown.contains(event.target)) {
        colorSchemeDropdown.classList.remove('open');
      }
    });

    // Add event listener for each option
    const options = optionsEl.querySelectorAll('.custom-dropdown-option');
    options.forEach(option => {
      option.addEventListener('click', () => {
        const selectedScheme = option.dataset.value;

        if (colorSchemeStatus) {
          colorSchemeStatus.textContent = 'Applying color scheme...';
        }

        // Remove 'selected' class from all options
        options.forEach(opt => opt.classList.remove('selected'));
        // Add 'selected' class to clicked option
        option.classList.add('selected');

        // Update toggle button text
        const textEl = toggleEl.querySelector('.custom-dropdown-toggle-text');
        if (textEl) {
          textEl.textContent = option.textContent;
        }

        // Apply the new color scheme
        applyColorScheme(selectedScheme);
        renderLegend(selectedScheme);

        // Close dropdown
        colorSchemeDropdown.classList.remove('open');

        if (colorSchemeStatus) {
          colorSchemeStatus.textContent = `Color scheme "${option.textContent}" applied.`;
        }
      });
    });
  } else {
    console.warn('Color scheme dropdown elements not found');
  }
} else {
  console.warn('Color scheme selector not found');
}

