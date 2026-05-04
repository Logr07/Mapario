const shapeModules = import.meta.glob("../assets/location-icons/shapes/*.svg", {
  eager: true,
  import: "default",
  query: "?raw",
});

const symbolModules = import.meta.glob("../assets/location-icons/symbols/*.svg", {
  eager: true,
  import: "default",
  query: "?url",
});

const DEFAULT_STATUS = "unsorted";
const DEFAULT_RATING = "unrated";
const DEFAULT_SUBCATEGORY = "other";

const OUTER_COLORS = {
  default: "#A0522D",
  favorite: "#E83E8C",
};

const RATING_COLORS = {
  unrated: "#FFFFFF",
  1: "#FF0000",
  2: "#FF7F00",
  3: "#FFFF00",
  4: "#00FF00",
  5: "#008000",
};

const SUBCATEGORY_SYMBOL_ALIASES = {
  defensive_structure: "defense_structure",
};

const shapes = normalizeGlobModules(shapeModules);
const symbols = normalizeGlobModules(symbolModules);
const shapeCache = new Map();

/**
 * Vrátí cache klíč identifikující vizulní styl ikony dané lokáce.
 * Používá se k rozlišení, zda Leaflet marker potřebuje překreslit.
 *
 * @param {object} location - Lokáce s volítelnými položkami `status`, `rating`, `subcategory`.
 * @returns {string}
 */
export function locationIconKey(location) {
  const status = normalizeStatus(location?.status);
  const rating = normalizeRating(location?.rating);
  const subcategory = normalizeSubcategory(location?.subcategory);
  return `lokace-${status}-${rating}-${subcategory}`;
}

/**
 * Vygeneruje HTML řetězec pro ikonu Leaflet markeru (SVG tvar + symbol podkategorie).
 *
 * @param {object} location - Lokáce s položkami `status`, `rating`, `subcategory`, `is_favorite`.
 * @returns {string} HTML fragment připravený k vložení do DivIcon.
 */
export function locationIconHtml(location) {
  const status = normalizeStatus(location?.status);
  const rating = normalizeRating(location?.rating);
  const subcategory = normalizeSubcategory(location?.subcategory);
  const symbolName = SUBCATEGORY_SYMBOL_ALIASES[subcategory] || subcategory;
  const symbolUrl = symbols[symbolName] || symbols[DEFAULT_SUBCATEGORY];
  const outerColor = location?.is_favorite ? OUTER_COLORS.favorite : OUTER_COLORS.default;
  const centerColor = RATING_COLORS[rating] || RATING_COLORS[DEFAULT_RATING];
  const iconKey = locationIconKey({ status, rating, subcategory });

  return `
    <span class="location-marker__icon" data-icon-key="${escapeAttribute(iconKey)}">
      ${shapeSvg(status, outerColor, centerColor)}
      <img class="location-marker__symbol" src="${escapeAttribute(symbolUrl)}" alt="" aria-hidden="true" />
    </span>
  `;
}

function shapeSvg(status, outerColor, centerColor) {
  const cacheKey = `${status}:${outerColor}:${centerColor}`;
  const cachedSvg = shapeCache.get(cacheKey);

  if (cachedSvg) {
    return cachedSvg;
  }

  const sourceSvg = shapes[status] || shapes[DEFAULT_STATUS];
  const coloredSvg = sourceSvg
    .replace("<svg ", '<svg class="location-marker__shape" aria-hidden="true" focusable="false" ')
    .replace(/fill="#A0522D"/gi, `fill="${outerColor}"`)
    .replace(/fill="(?:white|#fff|#ffffff)"/gi, `fill="${centerColor}"`);

  shapeCache.set(cacheKey, coloredSvg);
  return coloredSvg;
}

function normalizeGlobModules(modules) {
  return Object.fromEntries(
    Object.entries(modules).map(([path, value]) => {
      const name = path.split("/").pop().replace(/\.svg(?:\?.*)?$/, "");
      return [name, value];
    }),
  );
}

function normalizeStatus(value) {
  return shapes[value] ? value : DEFAULT_STATUS;
}

function normalizeRating(value) {
  return Object.hasOwn(RATING_COLORS, value) ? value : DEFAULT_RATING;
}

function normalizeSubcategory(value) {
  const symbolName = SUBCATEGORY_SYMBOL_ALIASES[value] || value;
  return symbols[symbolName] ? value : DEFAULT_SUBCATEGORY;
}

function escapeAttribute(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
