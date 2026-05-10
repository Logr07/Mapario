<script setup>
import L from "leaflet";
import "leaflet.markercluster";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

import { searchAddress, suggestAddresses } from "../api/geocoding";
import copyPopupIconUrl from "../assets/popup/copy.svg";
import deletePopupIconUrl from "../assets/popup/delete.svg";
import editPopupIconUrl from "../assets/popup/edit.svg";
import { formatDecimalCoordinates, parseCoordinates } from "../utils/coordinates";
import { locationIconHtml } from "../utils/locationIcons";
import {
  accessibilityOptions,
  categoryOptions,
  ratingOptions,
  statusOptions,
  subcategoryOptions,
} from "../utils/locationStructure";

const props = defineProps({
  locations: {
    type: Array,
    default: () => [],
  },
  filters: {
    type: Object,
    default: () => ({}),
  },
  selectedLocationId: {
    type: Number,
    default: null,
  },
  draftLocation: {
    type: Object,
    default: null,
  },
  baseLayer: {
    type: String,
    default: "osm",
  },
});

const emit = defineEmits([
  "select-location",
  "create-location",
  "toggle-favorite",
  "edit-location",
  "delete-location",
  "upload-photo",
  "delete-photo",
  "location-popup-open-change",
]);

const statusLabels = optionLabelMap(statusOptions);
const categoryLabels = optionLabelMap(categoryOptions);
const subcategoryLabels = optionLabelMap(subcategoryOptions);
const ratingLabels = optionLabelMap(ratingOptions);
const accessibilityLabels = optionLabelMap(accessibilityOptions);

const mapElement = ref(null);
const activeBaseLayer = ref("");
const searchQuery = ref("");
const searchStatus = ref("idle");
const searchError = ref("");
const searchResults = ref([]);
const mapToast = ref(null);
let map = null;
let osmLayer = null;
let googleSatelliteLayer = null;
let markersLayer = null;
let draftMarkersLayer = null;
let searchResultLayer = null;
let actionPopup = null;
let draftMarker = null;
let markersWereFit = false;
let markersByLocationId = new Map();
let visibleMarkerIds = new Set();
let photoIndexesByLocationId = new Map();
let openPopupLocationId = null;
let selectedMarkerLocationId = null;
let searchRequestVersion = 0;
let searchSuggestTimer = null;
let filterUpdateTimer = null;
let filterAnimationFrame = null;
let mapToastTimer = null;
let suppressSuggestionsForValue = "";

onMounted(() => {
  map = L.map(mapElement.value, {
    zoomControl: false,
  }).setView([49.8175, 15.473], 7);

  osmLayer = createOpenStreetMapLayer();
  googleSatelliteLayer = createGoogleSatelliteLayer();
  selectBaseLayer(props.baseLayer);

  L.control.zoom({ position: "bottomright" }).addTo(map);
  map.on("contextmenu", handleMapContextMenu);
  markersLayer = L.markerClusterGroup({
    animate: false,
    chunkDelay: 30,
    chunkedLoading: true,
    chunkInterval: 100,
    disableClusteringAtZoom: 14,
  }).addTo(map);
  draftMarkersLayer = L.layerGroup().addTo(map);
  searchResultLayer = L.layerGroup().addTo(map);
  syncMarkerCache();
  syncDraftMarker();
});

onBeforeUnmount(() => {
  emit("location-popup-open-change", false);
  clearSearchSuggestTimer();
  clearFilterUpdateTimer();
  clearMapToastTimer();
  if (map) {
    map.remove();
    map = null;
  }
});

watch(
  () => props.locations,
  () => {
    syncMarkerCache();
  },
);

watch(
  () => props.draftLocation,
  () => {
    syncDraftMarker();
  },
  { deep: true },
);

watch(
  () => props.filters,
  () => {
    scheduleFilterUpdate();
  },
  { deep: true },
);

watch(
  () => props.selectedLocationId,
  () => {
    updateMarkerSelection();
  },
);

watch(
  () => props.baseLayer,
  (layerKey) => {
    selectBaseLayer(layerKey);
  },
);

watch(searchQuery, (value) => {
  scheduleAddressSuggestions(value);
});

function syncMarkerCache() {
  if (!map || !markersLayer) {
    return;
  }

  const nextLocationIds = new Set();
  const bounds = [];

  props.locations.forEach((location) => {
    nextLocationIds.add(location.id);
    bounds.push([location.latitude, location.longitude]);

    const existingEntry = markersByLocationId.get(location.id);
    if (existingEntry) {
      updateMarkerEntry(existingEntry, location);
      return;
    }

    markersByLocationId.set(location.id, createMarkerEntry(location));
  });

  const removedMarkers = [];
  markersByLocationId.forEach((entry, locationId) => {
    if (nextLocationIds.has(locationId)) {
      return;
    }

    if (openPopupLocationId === locationId) {
      closeLocationPopup(entry);
    }
    if (entry.visible) {
      removedMarkers.push(entry.marker);
      visibleMarkerIds.delete(locationId);
    }
    markersByLocationId.delete(locationId);
  });

  if (removedMarkers.length > 0) {
    markersLayer.removeLayers(removedMarkers);
  }

  if (!markersWereFit && bounds.length > 0) {
    map.fitBounds(bounds, {
      maxZoom: 13,
      padding: [32, 32],
    });
    markersWereFit = true;
  }

  if (openPopupLocationId !== null && !markersByLocationId.has(openPopupLocationId)) {
    openPopupLocationId = null;
  }

  scheduleFilterUpdate();
}

function updateMarkerSelection() {
  const markerIdsToUpdate = new Set([selectedMarkerLocationId, props.selectedLocationId]);
  selectedMarkerLocationId = props.selectedLocationId;

  markerIdsToUpdate.forEach((locationId) => {
    if (locationId === null || locationId === undefined) {
      return;
    }
    const entry = markersByLocationId.get(locationId);
    if (entry) {
      entry.marker.setIcon(markerIcon(entry.location, entry.location.id === props.selectedLocationId));
    }
  });
}

function createMarkerEntry(location) {
  const marker = L.marker([location.latitude, location.longitude], {
    bubblingMouseEvents: false,
    icon: markerIcon(location, location.id === props.selectedLocationId),
    title: location.title,
  });
  const entry = {
    marker,
    location,
    filterCache: filterCacheForLocation(location),
    visible: false,
  };

  marker.on("click", () => emit("select-location", entry.location.id));
  marker.on("popupopen", () => {
    openPopupLocationId = entry.location.id;
    emit("location-popup-open-change", true);
    bindLocationPopup(marker, entry.location);
    scheduleLocationPopupReposition(marker, true);
  });
  marker.on("popupclose", () => {
    if (openPopupLocationId === entry.location.id) {
      openPopupLocationId = null;
      emit("location-popup-open-change", false);
    }
  });
  bindMarkerPopup(marker, location);

  return entry;
}

function updateMarkerEntry(entry, location) {
  const previousLocation = entry.location;
  entry.location = location;
  entry.filterCache = filterCacheForLocation(location);

  if (previousLocation.latitude !== location.latitude || previousLocation.longitude !== location.longitude) {
    entry.marker.setLatLng([location.latitude, location.longitude]);
  }

  if (previousLocation.title !== location.title) {
    entry.marker.options.title = location.title;
  }

  if (markerVisualKey(previousLocation) !== markerVisualKey(location) || location.id === props.selectedLocationId) {
    entry.marker.setIcon(markerIcon(location, location.id === props.selectedLocationId));
  }

  if (locationPopupDataKey(previousLocation) !== locationPopupDataKey(location)) {
    const popup = entry.marker.getPopup();
    if (popup?.isOpen()) {
      refreshLocationPopup(entry.marker, location);
      return;
    }

    bindMarkerPopup(entry.marker, location);
  }
}

function bindMarkerPopup(marker, location) {
  marker.bindPopup(locationPopupContent(location), {
    className: "location-popup",
    autoPan: false,
    autoPanPaddingBottomRight: [16, 96],
    autoPanPaddingTopLeft: [16, 92],
    closeButton: false,
    closeOnClick: false,
    keepInView: false,
    minWidth: 240,
    maxWidth: 380,
  });
}

function syncDraftMarker() {
  if (!draftMarkersLayer) {
    return;
  }

  if (!props.draftLocation) {
    if (draftMarker) {
      draftMarkersLayer.removeLayer(draftMarker);
      draftMarker = null;
    }
    return;
  }

  const latLng = [props.draftLocation.latitude, props.draftLocation.longitude];
  if (draftMarker) {
    draftMarker.setLatLng(latLng);
    return;
  }

  draftMarker = L.marker(latLng, {
    icon: draftMarkerIcon(),
    interactive: false,
  }).addTo(draftMarkersLayer);
}

function scheduleFilterUpdate() {
  if (!markersLayer) {
    return;
  }

  clearFilterUpdateTimer();
  filterUpdateTimer = window.setTimeout(() => {
    filterUpdateTimer = null;
    filterAnimationFrame = window.requestAnimationFrame(() => {
      filterAnimationFrame = null;
      applyMarkerFilters();
    });
  }, 80);
}

function clearFilterUpdateTimer() {
  if (filterUpdateTimer !== null) {
    window.clearTimeout(filterUpdateTimer);
    filterUpdateTimer = null;
  }
  if (filterAnimationFrame !== null) {
    window.cancelAnimationFrame(filterAnimationFrame);
    filterAnimationFrame = null;
  }
}

function applyMarkerFilters() {
  if (!markersLayer) {
    return;
  }

  const filterState = collectFilterState();
  const markersToAdd = [];
  const markersToRemove = [];

  markersByLocationId.forEach((entry, locationId) => {
    const shouldBeVisible = matchesFilter(entry.filterCache, filterState);

    if (shouldBeVisible && !entry.visible) {
      markersToAdd.push(entry.marker);
      entry.visible = true;
      visibleMarkerIds.add(locationId);
      return;
    }

    if (!shouldBeVisible && entry.visible) {
      if (openPopupLocationId === locationId) {
        closeLocationPopup(entry);
      }
      markersToRemove.push(entry.marker);
      entry.visible = false;
      visibleMarkerIds.delete(locationId);
    }
  });

  if (markersToRemove.length > 0) {
    markersLayer.removeLayers(markersToRemove);
  }
  if (markersToAdd.length > 0) {
    markersLayer.addLayers(markersToAdd);
  }
}

function closeLocationPopup(entry) {
  const popup = entry.marker.getPopup();
  if (popup?.isOpen()) {
    map?.closePopup(popup);
  }
}

function collectFilterState() {
  return {
    accessibilities: selectedFilterSet("accessibilities", accessibilityOptions.map((option) => option.value)),
    favorites: selectedFilterSet("favorites", ["favorite", "regular"]),
    ratings: selectedFilterSet("ratings", ratingOptions.map((option) => option.value)),
    statuses: selectedFilterSet("statuses", statusOptions.map((option) => option.value)),
    subcategories: selectedFilterSet("subcategories", subcategoryOptions.map((option) => option.value)),
  };
}

function selectedFilterSet(key, fallbackValues) {
  const values = props.filters?.[key];
  return new Set(Array.isArray(values) ? values : fallbackValues);
}

function filterCacheForLocation(location) {
  return {
    accessibility: location.accessibility,
    favoriteState: location.is_favorite ? "favorite" : "regular",
    rating: location.rating,
    status: location.status,
    subcategory: location.subcategory,
  };
}

function matchesFilter(filterCache, filterState) {
  return (
    filterState.statuses.has(filterCache.status) &&
    filterState.favorites.has(filterCache.favoriteState) &&
    filterState.subcategories.has(filterCache.subcategory) &&
    filterState.ratings.has(filterCache.rating) &&
    filterState.accessibilities.has(filterCache.accessibility)
  );
}

function markerVisualKey(location) {
  return [
    location.status,
    location.rating,
    location.subcategory,
    location.is_favorite ? "favorite" : "regular",
  ].join("|");
}

function locationPopupDataKey(location) {
  return JSON.stringify({
    accessibility: location.accessibility,
    category: location.category,
    created_at: location.created_at,
    id: location.id,
    is_favorite: location.is_favorite,
    latitude: location.latitude,
    longitude: location.longitude,
    photos: normalizePopupPhotos(location).map((photo) => `${photo.id}:${photo.url}`).join(","),
    rating: location.rating,
    status: location.status,
    subcategory: location.subcategory,
    title: location.title,
    updated_at: location.updated_at,
  });
}

function createOpenStreetMapLayer() {
  return L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  });
}

function createGoogleSatelliteLayer() {
  return L.tileLayer("https://{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", {
    maxZoom: 20,
    subdomains: ["mt0", "mt1", "mt2", "mt3"],
    attribution: "&copy; Google",
  });
}

function selectBaseLayer(layerKey) {
  const normalizedLayerKey = layerKey === "googleSatellite" ? "googleSatellite" : "osm";
  if (!map || activeBaseLayer.value === normalizedLayerKey) {
    return;
  }

  if (normalizedLayerKey === "osm") {
    switchBaseLayer(osmLayer, "osm");
    return;
  }

  if (normalizedLayerKey === "googleSatellite") {
    switchBaseLayer(googleSatelliteLayer, "googleSatellite");
    return;
  }
}

function switchBaseLayer(layer, layerKey) {
  if (!map || !layer) {
    return;
  }

  [osmLayer, googleSatelliteLayer].forEach((baseLayer) => {
    if (baseLayer && map.hasLayer(baseLayer)) {
      map.removeLayer(baseLayer);
    }
  });

  layer.addTo(map);
  activeBaseLayer.value = layerKey;
}

async function handleSearchSubmit() {
  const query = searchQuery.value.trim();
  searchError.value = "";
  searchResults.value = [];
  clearSearchSuggestTimer();

  if (!query) {
    searchError.value = "Zadej adresu nebo GPS souřadnice.";
    return;
  }

  const coordinates = parseCoordinates(query);
  if (coordinates) {
    searchStatus.value = "ready";
    focusSearchResult({
      id: "coordinates",
      display_name: formatDecimalCoordinates(coordinates.latitude, coordinates.longitude),
      latitude: coordinates.latitude,
      longitude: coordinates.longitude,
    });
    return;
  }

  const requestVersion = ++searchRequestVersion;
  searchStatus.value = "loading";
  try {
    const payload = await searchAddress(query);
    if (requestVersion !== searchRequestVersion) {
      return;
    }

    const results = Array.isArray(payload.results) ? payload.results : [];
    searchResults.value = results;
    if (results.length === 0) {
      searchError.value = "Nic jsem nenašel. Zkus upřesnit adresu.";
      clearSearchMarker();
      return;
    }

    focusSearchResult(results[0]);
  } catch (error) {
    if (requestVersion === searchRequestVersion) {
      searchError.value = error.message || "Vyhledávání se nepodařilo.";
    }
  } finally {
    if (requestVersion === searchRequestVersion) {
      searchStatus.value = "ready";
    }
  }
}

function selectSearchResult(result) {
  suppressSuggestionsForValue = result.display_name;
  focusSearchResult(result);
  searchQuery.value = result.display_name;
  searchResults.value = [];
  searchError.value = "";
}

function clearSearch() {
  ++searchRequestVersion;
  clearSearchSuggestTimer();
  searchQuery.value = "";
  searchError.value = "";
  searchResults.value = [];
  searchStatus.value = "idle";
  clearSearchMarker();
}

function scheduleAddressSuggestions(value) {
  clearSearchSuggestTimer();
  searchError.value = "";

  const query = value.trim();
  if (query === suppressSuggestionsForValue) {
    suppressSuggestionsForValue = "";
    searchStatus.value = "ready";
    searchResults.value = [];
    return;
  }

  if (query.length < 3) {
    ++searchRequestVersion;
    searchResults.value = [];
    searchStatus.value = "idle";
    return;
  }

  if (parseCoordinates(query)) {
    ++searchRequestVersion;
    searchResults.value = [];
    searchStatus.value = "ready";
    return;
  }

  const requestVersion = ++searchRequestVersion;
  searchStatus.value = "loading";
  searchSuggestTimer = window.setTimeout(() => {
    loadAddressSuggestions(query, requestVersion);
  }, 450);
}

async function loadAddressSuggestions(query, requestVersion) {
  try {
    const payload = await suggestAddresses(query);
    if (requestVersion !== searchRequestVersion) {
      return;
    }

    searchResults.value = Array.isArray(payload.results) ? payload.results : [];
  } catch (error) {
    if (requestVersion === searchRequestVersion) {
      searchResults.value = [];
      searchError.value = error.message || "Našeptávání se nepodařilo.";
    }
  } finally {
    if (requestVersion === searchRequestVersion) {
      searchStatus.value = "ready";
    }
  }
}

function clearSearchSuggestTimer() {
  if (searchSuggestTimer !== null) {
    window.clearTimeout(searchSuggestTimer);
    searchSuggestTimer = null;
  }
}

function focusSearchResult(result) {
  if (!map || !searchResultLayer) {
    return;
  }

  const latitude = Number(result.latitude);
  const longitude = Number(result.longitude);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    searchError.value = "Vyhledaný výsledek nemá platné souřadnice.";
    return;
  }

  clearSearchMarker();
  map.closePopup();

  const latLng = L.latLng(latitude, longitude);
  const marker = L.marker(latLng, {
    icon: searchMarkerIcon(),
    title: result.display_name,
    zIndexOffset: 1200,
  });

  marker.bindPopup(searchPopupContent(result), {
    className: "search-result-popup",
    closeButton: true,
    maxWidth: 300,
    closeOnClick: false,
  });
  marker.addTo(searchResultLayer).openPopup();

  const bounds = searchResultBounds(result);
  if (bounds?.isValid()) {
    map.fitBounds(bounds, {
      maxZoom: 17,
      padding: [64, 64],
    });
    return;
  }

  map.setView(latLng, Math.max(map.getZoom(), 16), {
    animate: true,
  });
}

function clearSearchMarker() {
  searchResultLayer?.clearLayers();
}

function searchResultBounds(result) {
  const boundingBox = result?.bounding_box;
  if (!boundingBox) {
    return null;
  }

  const south = Number(boundingBox.south);
  const west = Number(boundingBox.west);
  const north = Number(boundingBox.north);
  const east = Number(boundingBox.east);
  if (![south, west, north, east].every(Number.isFinite)) {
    return null;
  }

  return L.latLngBounds([
    [south, west],
    [north, east],
  ]);
}

function searchPopupContent(result) {
  return `
    <div class="search-result-popup__content">
      <strong>${escapeHtml(result.display_name)}</strong>
      <span>${formatCoordinates(result)}</span>
    </div>
  `;
}

function handleMapContextMenu(event) {
  openActionPopup(event.latlng);
}

function openActionPopup(latlng) {
  if (!map) {
    return;
  }

  const coordinates = {
    latitude: latlng.lat,
    longitude: latlng.lng,
  };
  const formattedCoordinates = formatCoordinates(coordinates);
  actionPopup = L.popup({
    className: "map-action-popup",
    closeButton: true,
    minWidth: 220,
    maxWidth: 260,
  })
    .setLatLng(latlng)
    .setContent(`
      <div class="map-action-popup__content">
        <strong class="map-action-popup__title">Vyber akci:</strong>
        <button class="map-action-popup__button" type="button" data-action="copy">Zkopíruj souřadnice</button>
        <button class="map-action-popup__button" type="button" data-action="mapycz">Otevři v Mapách.cz</button>
        <button class="map-action-popup__button" type="button" data-action="google">Otevři v Google Maps</button>
        <button class="map-action-popup__button map-action-popup__button--primary" type="button" data-action="create">Přidej lokaci</button>
      </div>
    `)
    .openOn(map);

  bindActionPopup(coordinates, formattedCoordinates);
}

function bindActionPopup(coordinates, formattedCoordinates) {
  const element = actionPopup?.getElement();
  if (!element) {
    return;
  }

  L.DomEvent.disableClickPropagation(element);

  element.querySelector('[data-action="copy"]')?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    const copied = await copyCoordinates(formattedCoordinates);

    if (copied) {
      map?.closePopup(actionPopup);
      actionPopup = null;
      showMapToast("Souřadnice zkopírovány.");
      return;
    }

    button.disabled = false;
    showMapToast("Souřadnice se nepodařilo zkopírovat.", "error");
  });

  element.querySelector('[data-action="mapycz"]')?.addEventListener("click", () => {
    window.open(
      `https://mapy.cz/zakladni?x=${coordinates.longitude}&y=${coordinates.latitude}&z=17`,
      "_blank",
      "noopener,noreferrer",
    );
  });

  element.querySelector('[data-action="google"]')?.addEventListener("click", () => {
    window.open(
      `https://www.google.com/maps/search/?api=1&query=${coordinates.latitude},${coordinates.longitude}`,
      "_blank",
      "noopener,noreferrer",
    );
  });

  element.querySelector('[data-action="create"]')?.addEventListener("click", () => {
    map.closePopup(actionPopup);
    emit("create-location", coordinates);
  });
}

async function copyCoordinates(coordinates) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(coordinates);
      return true;
    }

    const input = document.createElement("textarea");
    try {
      input.value = coordinates;
      input.setAttribute("readonly", "");
      input.style.position = "fixed";
      input.style.opacity = "0";
      document.body.appendChild(input);
      input.select();
      return document.execCommand("copy");
    } finally {
      input.remove();
    }
  } catch {
    return false;
  }
}

function showMapToast(message, type = "success") {
  clearMapToastTimer();
  mapToast.value = { message, type };
  mapToastTimer = window.setTimeout(() => {
    mapToast.value = null;
    mapToastTimer = null;
  }, 2500);
}

function clearMapToastTimer() {
  if (mapToastTimer) {
    window.clearTimeout(mapToastTimer);
    mapToastTimer = null;
  }
}

function formatCoordinates(coordinates) {
  return `${Number(coordinates.latitude).toFixed(6)}, ${Number(coordinates.longitude).toFixed(6)}`;
}

function locationPopupContent(location) {
  const popupLocation = normalizePopupLocation(location);
  const isFavorite = popupLocation.is_favorite;
  const favoriteLabel = isFavorite ? "Odebrat z oblíbených" : "Přidat do oblíbených";

  return `
    <div class="location-popup__content">
      <div class="location-popup__topbar">
        <button
          class="location-popup__icon-action location-popup__favorite${isFavorite ? " location-popup__favorite--active" : ""}"
          type="button"
          data-action="favorite"
          aria-label="${escapeHtml(favoriteLabel)}"
          title="${escapeHtml(favoriteLabel)}"
        >
          <span aria-hidden="true">${isFavorite ? "★" : "☆"}</span>
        </button>
        <div class="location-popup__category">
          <span>Kategorie</span>
          <strong>${escapeHtml(labelFor(categoryLabels, popupLocation.category))}</strong>
        </div>
        <button
          class="location-popup__icon-action location-popup__close"
          type="button"
          data-action="close"
          aria-label="Zavřít popup"
          title="Zavřít popup"
        >×</button>
      </div>
      <section class="location-popup__summary">
        <span class="location-popup__kicker">Popis lokace</span>
        <strong class="location-popup__title">${escapeHtml(popupLocation.title)}</strong>
      </section>
      <dl class="location-popup__attributes">
        ${locationAttribute("Typ", subcategoryShortLabel(popupLocation.subcategory))}
        ${locationAttribute("Stav", labelFor(statusLabels, popupLocation.status))}
        ${locationAttribute("Hodnocení", labelFor(ratingLabels, popupLocation.rating))}
        ${locationAttribute("Přístupnost", labelFor(accessibilityLabels, popupLocation.accessibility))}
      </dl>
      <div class="location-popup__dates">
        ${dateCard("Přidáno", popupLocation.created_at)}
        ${dateCard("Upraveno", popupLocation.updated_at)}
      </div>
      ${photoGallery(popupLocation)}
      <div class="location-popup__actions">
        ${popupActionButton("edit", editPopupIconUrl, "Upravit", "Upravit lokaci")}
        ${popupActionButton("copy", copyPopupIconUrl, "GPS", "Zkopírovat GPS")}
        ${popupActionButton("delete", deletePopupIconUrl, "Smazat", "Smazat lokaci")}
      </div>
    </div>
  `;
}

function bindLocationPopup(marker, location) {
  const element = marker.getPopup()?.getElement();
  if (!element) {
    return;
  }

  L.DomEvent.disableClickPropagation(element);
  L.DomEvent.disableScrollPropagation(element);

  bindPopupButton(element, "copy", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    const copied = await copyCoordinates(formatCoordinates(location));

    if (copied) {
      map?.closePopup(marker.getPopup());
      showMapToast("Souřadnice zkopírovány.");
      return;
    }

    button.disabled = false;
    showMapToast("Souřadnice se nepodařilo zkopírovat.", "error");
  });

  bindPopupButton(element, "favorite", (event) => {
    event.currentTarget.disabled = true;
    emit("toggle-favorite", {
      locationId: location.id,
      isFavorite: !location.is_favorite,
    });
  });

  bindPopupButton(element, "close", () => {
    map?.closePopup(marker.getPopup());
  });

  bindPopupButton(element, "edit", () => {
    map?.closePopup(marker.getPopup());
    emit("edit-location", location.id);
  });

  bindPopupButton(element, "delete", (event) => {
    event.currentTarget.disabled = true;
    map?.closePopup(marker.getPopup());
    emit("delete-location", location.id);
  });

  bindPopupButton(element, "previous-photo", () => {
    movePhotoIndex(location, -1);
    refreshLocationPopup(marker, location);
  });

  bindPopupButton(element, "next-photo", () => {
    movePhotoIndex(location, 1);
    refreshLocationPopup(marker, location);
  });

  const uploadInput = element.querySelector('[data-action="upload-photo"]');
  if (uploadInput) {
    uploadInput.onchange = (event) => {
      const file = event.currentTarget.files?.[0];
      if (file) {
        emit("upload-photo", {
          locationId: location.id,
          file,
        });
      }
      event.currentTarget.value = "";
    };
  }

  element.querySelectorAll('[data-action="delete-photo"]').forEach((button) => {
    button.onclick = (event) => {
      emit("delete-photo", {
        locationId: location.id,
        photoId: Number(event.currentTarget.dataset.photoId),
      });
    };
  });

  bindPopupPhotoLoadErrors(element, marker, location);
}

function refreshLocationPopup(marker, location) {
  const popup = marker.getPopup();
  if (!popup) {
    return;
  }

  const scrollContainer = popup.getElement()?.querySelector('.leaflet-popup-content');
  const scrollTop = scrollContainer ? scrollContainer.scrollTop : 0;

  popup.setContent(locationPopupContent(location));
  popup.update();
  bindLocationPopup(marker, location);

  const newScrollContainer = popup.getElement()?.querySelector('.leaflet-popup-content');
  if (newScrollContainer) {
    newScrollContainer.scrollTop = scrollTop;
  }

  scheduleLocationPopupReposition(marker, false);
}

function scheduleLocationPopupReposition(marker, animate = false) {
  window.requestAnimationFrame(() => {
    repositionLocationPopup(marker, animate);
    window.requestAnimationFrame(() => repositionLocationPopup(marker, false));
  });
}

function repositionLocationPopup(marker, animate = false) {
  const popup = marker.getPopup();
  const popupElement = popup?.getElement();
  if (!map || !popup?.isOpen() || !popupElement) {
    return;
  }

  const safeFrame = getLocationPopupSafeFrame();
  const mapRect = map.getContainer().getBoundingClientRect();
  const availableBottom = Math.max(safeFrame.top + 1, safeFrame.bottom - safeFrame.bottomReserve);
  const availableHeight = Math.max(1, availableBottom - safeFrame.top);
  popupElement.style.setProperty("--location-popup-wrapper-max-height", `${Math.max(180, availableHeight)}px`);
  popupElement.style.setProperty("--location-popup-content-max-height", `${Math.max(150, availableHeight - 34)}px`);
  const popupRect = popupElement.getBoundingClientRect();
  if (!popupRect.width || !popupRect.height) {
    return;
  }

  const minLeft = safeFrame.left;
  const maxLeft = Math.max(minLeft, safeFrame.right - popupRect.width);
  const centeredLeft = safeFrame.left + (safeFrame.width - popupRect.width) / 2;
  const desiredLeft = Math.max(minLeft, Math.min(maxLeft, centeredLeft));
  const centeredTop = safeFrame.top + Math.max(0, (availableHeight - popupRect.height) / 2);
  const desiredTop = Math.max(
    safeFrame.top,
    Math.min(Math.max(safeFrame.top, availableBottom - popupRect.height), safeFrame.isMobile ? safeFrame.top : centeredTop),
  );
  const currentMarkerPoint = map.latLngToContainerPoint(marker.getLatLng());
  const currentPopupPoint = L.point(popupRect.left - mapRect.left, popupRect.top - mapRect.top);
  const desiredPopupPoint = L.point(desiredLeft - mapRect.left, desiredTop - mapRect.top);
  const delta = desiredPopupPoint.subtract(currentPopupPoint);

  if (Math.abs(delta.x) < 1 && Math.abs(delta.y) < 1) {
    return;
  }

  const zoom = map.getZoom();
  const markerProjectedPoint = map.project(marker.getLatLng(), zoom);
  const targetMarkerPoint = currentMarkerPoint.add(delta);
  const targetCenterPoint = markerProjectedPoint.subtract(targetMarkerPoint).add(map.getSize().divideBy(2));

  map.panTo(map.unproject(targetCenterPoint, zoom), {
    animate,
    duration: animate ? 0.18 : 0,
    easeLinearity: 0.2,
    noMoveStart: true,
  });
}

function getLocationPopupSafeFrame() {
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
  const isMobile = isMobileViewport();
  const edgePadding = isMobile ? 10 : 16;
  const mapRect = map?.getContainer().getBoundingClientRect();
  let left = Math.max(edgePadding, Math.ceil(mapRect?.left || 0) + edgePadding);
  let right = Math.min(viewportWidth - edgePadding, Math.floor(mapRect?.right || viewportWidth) - edgePadding);
  let top = Math.max(edgePadding, Math.ceil(mapRect?.top || 0) + edgePadding);
  let bottom = Math.min(viewportHeight - edgePadding, Math.floor(mapRect?.bottom || viewportHeight) - edgePadding);

  [".topbar", ".map-search"].forEach((selector) => {
    const blockingRect = document.querySelector(selector)?.getBoundingClientRect();
    if (
      blockingRect &&
      blockingRect.bottom > 0 &&
      blockingRect.top < viewportHeight &&
      blockingRect.right > left &&
      blockingRect.left < right
    ) {
      top = Math.max(top, Math.ceil(blockingRect.bottom + (isMobile ? 10 : 16)));
    }
  });

  if (right <= left + 80) {
    left = edgePadding;
    right = viewportWidth - edgePadding;
  }

  if (bottom <= top + 120) {
    top = edgePadding;
    bottom = viewportHeight - edgePadding;
  }

  return {
    isMobile,
    left,
    top,
    right,
    bottom,
    width: Math.max(150, right - left),
    height: Math.max(160, bottom - top),
    bottomReserve: isMobile ? Math.max(72, Math.round(viewportHeight * 0.1)) : 42,
  };
}

function movePhotoIndex(location, direction) {
  const photos = normalizePopupPhotos(location);
  if (photos.length < 2) {
    return;
  }

  const currentIndex = currentPhotoIndexForPhotos(location.id, photos);
  const nextIndex = (currentIndex + direction + photos.length) % photos.length;
  photoIndexesByLocationId.set(location.id, nextIndex);
}

function bindPopupButton(element, action, handler) {
  const button = element.querySelector(`[data-action="${action}"]`);
  if (button) {
    button.onclick = handler;
  }
}

function locationAttribute(label, value) {
  return `
    <div>
      <dt>${escapeHtml(label)}</dt>
      <dd>${escapeHtml(value)}</dd>
    </div>
  `;
}

function dateCard(label, value) {
  return `
    <section class="location-popup__date-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(formatPopupDate(value))}</strong>
    </section>
  `;
}

function formatPopupDate(value) {
  if (!value) {
    return "Neuvedeno";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Neuvedeno";
  }

  return new Intl.DateTimeFormat("cs-CZ", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function popupActionButton(action, iconUrl, label, title) {
  return `
    <button
      class="location-popup__action location-popup__action--${escapeHtml(action)}"
      type="button"
      data-action="${escapeHtml(action)}"
      title="${escapeHtml(title)}"
      aria-label="${escapeHtml(title)}"
    >
      <img class="location-popup__action-icon" src="${escapeHtml(iconUrl)}" alt="" aria-hidden="true" />
      <span class="location-popup__action-label">${escapeHtml(label)}</span>
    </button>
  `;
}

function photoGallery(location) {
  const photos = normalizePopupPhotos(location);
  const photoIndex = currentPhotoIndexForPhotos(location.id, photos);
  const currentPhoto = photos[photoIndex];
  const galleryContent = currentPhoto
    ? `
      <div class="location-popup__photo-carousel">
        ${photoItem(currentPhoto, photoIndex, photos.length)}
      </div>
    `
    : '<p class="location-popup__photos-empty">Bez fotek</p>';

  return `
    <section class="location-popup__photos${currentPhoto ? "" : " location-popup__photos--empty"}" aria-label="Fotodokumentace">
      <div class="location-popup__photos-header">
        <span>Fotky</span>
        <span>${photos.length > 0 ? `${photoIndex + 1} / ${photos.length}` : "0"}</span>
      </div>
      ${galleryContent}
      <label class="location-popup__upload">
        Nahrát fotku
        <input type="file" accept="image/*" data-action="upload-photo" />
      </label>
    </section>
  `;
}

function photoItem(photo, photoIndex, photoCount) {
  const disabledAttribute = photoCount < 2 ? "disabled" : "";
  return `
    <figure class="location-popup__photo">
      <img
        src="${escapeHtml(photo.url)}"
        alt="${escapeHtml(photo.original_filename)}"
        loading="lazy"
        data-photo-id="${escapeHtml(photo.id)}"
      />
      <button
        class="location-popup__photo-nav location-popup__photo-nav--previous"
        type="button"
        data-action="previous-photo"
        title="Předchozí fotka"
        ${disabledAttribute}
      ></button>
      <button
        class="location-popup__photo-nav location-popup__photo-nav--next"
        type="button"
        data-action="next-photo"
        title="Další fotka"
        ${disabledAttribute}
      ></button>
      <button
        class="location-popup__photo-delete"
        type="button"
        data-action="delete-photo"
        data-photo-id="${escapeHtml(photo.id)}"
        title="Smazat fotku"
      >×</button>
    </figure>
  `;
}

function currentPhotoIndexForPhotos(locationId, photos) {
  if (photos.length === 0) {
    photoIndexesByLocationId.delete(locationId);
    return 0;
  }

  const storedIndex = photoIndexesByLocationId.get(locationId) ?? 0;
  const normalizedIndex = Math.min(Math.max(storedIndex, 0), photos.length - 1);
  photoIndexesByLocationId.set(locationId, normalizedIndex);
  return normalizedIndex;
}

function bindPopupPhotoLoadErrors(element, marker, location) {
  element.querySelectorAll(".location-popup__photo img[data-photo-id]").forEach((image) => {
    const photoId = Number(image.dataset.photoId);
    const showFallback = () => showBrokenPhotoFallback(image, marker, location.id, photoId);
    image.onerror = showFallback;

    if (image.complete && image.naturalWidth === 0) {
      showFallback();
    }
  });
}

function showBrokenPhotoFallback(image, marker, locationId, photoId) {
  const carousel = image.closest(".location-popup__photo-carousel");
  if (!carousel || carousel.classList.contains("location-popup__photo-carousel--compact")) {
    return;
  }

  const deleteButton = Number.isFinite(photoId)
    ? `
      <button
        class="location-popup__photo-unavailable-delete"
        type="button"
        data-action="delete-photo"
        data-photo-id="${escapeHtml(photoId)}"
      >Smazat záznam</button>
    `
    : "";

  carousel.classList.add("location-popup__photo-carousel--compact");
  carousel.innerHTML = `
    <div class="location-popup__photo-unavailable">
      <span>Fotku se nepodařilo načíst.</span>
      ${deleteButton}
    </div>
  `;

  carousel.querySelector('[data-action="delete-photo"]')?.addEventListener("click", () => {
    emit("delete-photo", { locationId, photoId });
  });

  scheduleLocationPopupReposition(marker, false);
}

function normalizePopupLocation(location) {
  return {
    ...location,
    title: normalizePopupText(location?.title),
    category: normalizePopupValue(location?.category),
    subcategory: normalizePopupValue(location?.subcategory),
    status: normalizePopupValue(location?.status),
    rating: normalizePopupValue(location?.rating),
    accessibility: normalizePopupValue(location?.accessibility),
    created_at: location?.created_at,
    updated_at: location?.updated_at,
    is_favorite: Boolean(location?.is_favorite),
    photos: normalizePopupPhotos(location),
  };
}

function normalizePopupPhotos(location) {
  if (!Array.isArray(location?.photos)) {
    return [];
  }

  return location.photos.reduce((photos, photo) => {
    if (!photo || typeof photo !== "object") {
      return photos;
    }

    const photoId = normalizePopupPhotoId(photo.id);
    const url = normalizePopupUrl(photo.url);
    if (photoId === null || !url) {
      return photos;
    }

    photos.push({
      ...photo,
      id: photoId,
      url,
      original_filename: normalizePopupText(photo.original_filename, "Fotka"),
    });
    return photos;
  }, []);
}

function normalizePopupPhotoId(value) {
  const photoId = Number(value);
  return Number.isInteger(photoId) && photoId > 0 ? photoId : null;
}

function normalizePopupUrl(value) {
  const url = normalizePopupValue(value);
  return url && url !== "null" && url !== "undefined" ? url : "";
}

function normalizePopupText(value, fallback = "Neuvedeno") {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  return text || fallback;
}

function normalizePopupValue(value) {
  return String(value ?? "").trim();
}

function optionLabelMap(options) {
  return new Map(options.map((option) => [option.value, option.label]));
}

function labelFor(labelMap, value) {
  return labelMap.get(value) || "Neuvedeno";
}

function subcategoryShortLabel(value) {
  const label = labelFor(subcategoryLabels, value);
  const separatorIndex = label.indexOf(": ");
  return separatorIndex === -1 ? label : label.slice(separatorIndex + 2);
}

function markerIcon(location, isSelected) {
  return L.divIcon({
    className: `location-marker location-marker--custom${isSelected ? " location-marker--selected" : ""}${
      location.is_favorite ? " location-marker--favorite" : ""
    }`,
    html: locationIconHtml(location),
    iconSize: [46, 46],
    iconAnchor: [23, 23],
  });
}

function draftMarkerIcon() {
  return L.divIcon({
    className: "location-marker location-marker--draft",
    html: '<span class="location-marker__dot"></span>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

function searchMarkerIcon() {
  return L.divIcon({
    className: "search-result-marker",
    html: '<span class="search-result-marker__pin"></span>',
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });
}

function isMobileViewport() {
  return typeof window !== "undefined" && window.matchMedia("(max-width: 640px)").matches;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
</script>

<template>
  <section class="map-stage" aria-label="Mapa evidovaných lokalit">
    <div ref="mapElement" class="map-view"></div>
    <p
      v-if="mapToast"
      class="map-toast"
      :class="`map-toast--${mapToast.type}`"
      role="status"
      aria-live="polite"
    >
      {{ mapToast.message }}
    </p>
    <form
      class="map-search"
      role="search"
      aria-label="Vyhledat místo v mapě"
      @submit.prevent="handleSearchSubmit"
      @click.stop
      @dblclick.stop
      @mousedown.stop
      @touchstart.stop
    >
      <label class="visually-hidden" for="map-search-input">Adresa nebo GPS souřadnice</label>
      <div class="map-search__row">
        <input
          id="map-search-input"
          v-model="searchQuery"
          class="map-search__input"
          type="text"
          inputmode="search"
          autocomplete="off"
          spellcheck="false"
          placeholder="Adresa nebo GPS"
          :aria-expanded="searchResults.length > 0"
          aria-controls="map-search-results"
          @keydown.esc="searchResults = []"
        />
        <button v-if="searchQuery" class="map-search__clear" type="button" title="Vymazat hledání" @click="clearSearch">
          ×
        </button>
        <button class="map-search__submit" type="submit" :disabled="searchStatus === 'loading' || !searchQuery.trim()">
          {{ searchStatus === "loading" ? "Hledám..." : "Hledat" }}
        </button>
      </div>
      <p v-if="searchError" class="map-search__message map-search__message--error">{{ searchError }}</p>
      <ul v-if="searchResults.length > 0" id="map-search-results" class="map-search__results">
        <li v-for="result in searchResults" :key="result.id">
          <button type="button" class="map-search__result" @click="selectSearchResult(result)">
            <span>{{ result.display_name }}</span>
            <small>{{ formatCoordinates(result) }}</small>
          </button>
        </li>
      </ul>
    </form>
  </section>
</template>
