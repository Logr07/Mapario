/**
 * Pokusí se parsovat textový vstup jako souřadnice (desetinné, DMS, s/bez směrového písmene).
 *
 * @param {string} input
 * @returns {{ latitude: number, longitude: number } | null} Parsované souřadnice, nebo `null` při selhání.
 */
export function parseCoordinates(input) {
  const text = String(input || "").trim();
  if (!text) {
    return null;
  }

  const dmsCoordinates = parseDmsCoordinates(text);
  if (dmsCoordinates) {
    return dmsCoordinates;
  }

  const normalizedText = text.replace(/[()[\]]/g, " ");
  const matches = [...normalizedText.matchAll(/([+-]?\d+(?:[.,]\d+)?)(?:\s*°)?\s*([NSEW])?/gi)];
  let tokens = matches.map((match) => ({
    value: parseLocalizedNumber(match[1]),
    direction: match[2]?.toUpperCase() || "",
  }));

  if (tokens.length === 1 && normalizedText.includes(",")) {
    tokens = normalizedText.split(",").map((part) => ({
      value: parseLocalizedNumber(part),
      direction: "",
    }));
  }

  if (tokens.length < 2) {
    return null;
  }

  return normalizeCoordinatePair(tokens[0], tokens[1]);
}

/**
 * Formátuje souřadnice jako čitelny řetězec s desetinnými stupni.
 *
 * @param {number} latitude
 * @param {number} longitude
 * @returns {string} Např. "50.0755, 14.4378"
 */
export function formatDecimalCoordinates(latitude, longitude) {
  return `${roundCoordinate(Number(latitude))}, ${roundCoordinate(Number(longitude))}`;
}

function parseDmsCoordinates(input) {
  if (!input.includes("°")) {
    return null;
  }

  const pattern =
    /([+-]?\d+(?:[.,]\d+)?)\s*°\s*(\d+(?:[.,]\d+)?)?\s*(?:['′])?\s*(\d+(?:[.,]\d+)?)?\s*(?:"|″)?\s*([NSEW])?/gi;
  const tokens = [...input.matchAll(pattern)].map((match) => ({
    value: dmsToDecimal(match[1], match[2], match[3]),
    direction: match[4]?.toUpperCase() || "",
  }));

  if (tokens.length < 2) {
    return null;
  }

  return normalizeCoordinatePair(tokens[0], tokens[1]);
}

function normalizeCoordinatePair(first, second) {
  if (!Number.isFinite(first.value) || !Number.isFinite(second.value)) {
    return null;
  }

  let latitudeToken = first;
  let longitudeToken = second;
  if (isLongitudeDirection(first.direction) && isLatitudeDirection(second.direction)) {
    latitudeToken = second;
    longitudeToken = first;
  }

  const latitude = applyDirection(latitudeToken.value, latitudeToken.direction);
  const longitude = applyDirection(longitudeToken.value, longitudeToken.direction);

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    return null;
  }
  if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    return null;
  }

  return {
    latitude: roundCoordinate(latitude),
    longitude: roundCoordinate(longitude),
  };
}

function dmsToDecimal(degrees, minutes = "0", seconds = "0") {
  const degreeValue = parseLocalizedNumber(degrees);
  const minuteValue = parseLocalizedNumber(minutes);
  const secondValue = parseLocalizedNumber(seconds);
  const sign = degreeValue < 0 ? -1 : 1;
  return sign * (Math.abs(degreeValue) + minuteValue / 60 + secondValue / 3600);
}

function applyDirection(value, direction) {
  const absoluteValue = Math.abs(value);
  if (direction === "S" || direction === "W") {
    return -absoluteValue;
  }
  if (direction === "N" || direction === "E") {
    return absoluteValue;
  }
  return value;
}

function parseLocalizedNumber(value) {
  return Number(String(value || "").trim().replace(",", "."));
}

function isLatitudeDirection(direction) {
  return direction === "N" || direction === "S";
}

function isLongitudeDirection(direction) {
  return direction === "E" || direction === "W";
}

function roundCoordinate(value) {
  return Number(value.toFixed(7));
}
