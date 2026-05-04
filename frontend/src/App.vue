<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";

import { getCurrentUser, loginUser, logoutUser, registerUser } from "./api/auth";
import { getHealth } from "./api/health";
import { createLocation, deleteLocation, listLocations, setLocationFavorite, updateLocation } from "./api/locations";
import { deleteLocationPhoto, listLocationPhotos, uploadLocationPhoto } from "./api/photos";
import AuthPanel from "./components/AuthPanel.vue";
import ChangePasswordPanel from "./components/ChangePasswordPanel.vue";
import LocationFilters from "./components/LocationFilters.vue";
import LocationFormPanel from "./components/LocationFormPanel.vue";
import MapView from "./components/MapView.vue";
import { accessibilityOptions, ratingOptions, statusOptions, subcategoryOptions } from "./utils/locationStructure";

const apiStatus = ref("checking");
const authStatus = ref("checking");
const authError = ref("");
const currentUser = ref(null);
const isSubmitting = ref(false);
const locations = ref([]);
const locationsError = ref("");
const locationsStatus = ref("idle");
const isFilterPanelOpen = ref(false);
const editorMode = ref("");
const editorLocation = ref(null);
const editorError = ref("");
const isEditorSubmitting = ref(false);
const selectedLocationId = ref(null);
const isLocationPopupOpen = ref(false);
const selectedBaseLayer = ref("osm");
const isChangePasswordOpen = ref(false);
let authRequestVersion = 0;
const favoriteOptions = [
  { value: "favorite", label: "Oblíbené" },
  { value: "regular", label: "Ostatní" },
];
const baseLayerOptions = [
  { value: "osm", label: "Geografická", title: "Geografická mapa" },
  { value: "googleSatellite", label: "Letecká", title: "Letecká mapa" },
];
const isAuthBusy = computed(() => isSubmitting.value);
const defaultFilters = {
  favorites: favoriteOptions.map((option) => option.value),
  subcategories: subcategoryOptions.map((option) => option.value),
  statuses: statusOptions.map((option) => option.value),
  ratings: ratingOptions.map((option) => option.value),
  accessibilities: accessibilityOptions.map((option) => option.value),
};
const filters = reactive(createDefaultFilters());

const activeFilterCount = computed(
  () =>
    defaultFilters.favorites.length -
    filters.favorites.length +
    defaultFilters.statuses.length -
    filters.statuses.length +
    defaultFilters.subcategories.length -
    filters.subcategories.length +
    defaultFilters.ratings.length -
    filters.ratings.length +
    defaultFilters.accessibilities.length -
    filters.accessibilities.length,
);

const filteredLocations = computed(() =>
  locations.value.filter(
    (location) =>
      matchesSelected(filters.statuses, location.status) &&
      matchesSelected(filters.favorites, location.is_favorite ? "favorite" : "regular") &&
      matchesSelected(filters.subcategories, location.subcategory) &&
      matchesSelected(filters.ratings, location.rating) &&
      matchesSelected(filters.accessibilities, location.accessibility),
  ),
);

onMounted(async () => {
  await Promise.all([checkApiHealth(), loadCurrentUser()]);
});

watch(currentUser, async (user) => {
  if (user) {
    await loadLocations();
    return;
  }

  locations.value = [];
  selectedLocationId.value = null;
  isLocationPopupOpen.value = false;
  isFilterPanelOpen.value = false;
  closeLocationEditor();
  resetFilters();
});

watch(filteredLocations, (visibleLocations) => {
  if (
    selectedLocationId.value !== null &&
    !visibleLocations.some((location) => location.id === selectedLocationId.value)
  ) {
    selectedLocationId.value = null;
  }
});

async function checkApiHealth() {
  try {
    await getHealth();
    apiStatus.value = "online";
  } catch {
    apiStatus.value = "offline";
  }
}

async function loadCurrentUser() {
  const requestVersion = ++authRequestVersion;
  authStatus.value = "checking";
  try {
    const payload = await getCurrentUser({ timeoutMs: 8000 });
    if (requestVersion !== authRequestVersion) {
      return;
    }
    currentUser.value = payload.authenticated ? payload.user : null;
  } catch {
    if (requestVersion !== authRequestVersion) {
      return;
    }
    currentUser.value = null;
  } finally {
    if (requestVersion === authRequestVersion) {
      authStatus.value = "ready";
    }
  }
}

async function handleLogin(payload) {
  await submitAuth(() => loginUser(payload));
}

async function handleRegister(payload) {
  await submitAuth(() => registerUser(payload));
}

async function submitAuth(action) {
  if (isAuthBusy.value) {
    return;
  }

  const requestVersion = ++authRequestVersion;
  authStatus.value = "ready";
  authError.value = "";
  isSubmitting.value = true;
  try {
    const payload = await action();
    if (requestVersion !== authRequestVersion) {
      return;
    }
    currentUser.value = payload.user;
  } catch (error) {
    if (requestVersion === authRequestVersion) {
      authError.value = error.message || "Akci se nepodařilo dokončit.";
    }
  } finally {
    if (requestVersion === authRequestVersion) {
      isSubmitting.value = false;
    }
  }
}

async function handleLogout() {
  const requestVersion = ++authRequestVersion;
  authError.value = "";
  isSubmitting.value = true;
  try {
    await logoutUser();
    if (requestVersion === authRequestVersion) {
      currentUser.value = null;
    }
  } catch (error) {
    if (requestVersion === authRequestVersion) {
      authError.value = error.message || "Odhlášení se nepodařilo dokončit.";
    }
  } finally {
    if (requestVersion === authRequestVersion) {
      isSubmitting.value = false;
    }
  }
}

async function loadLocations() {
  locationsStatus.value = "loading";
  locationsError.value = "";
  try {
    const payload = await listLocations();
    locations.value = await attachPhotos(payload.locations || []);
  } catch (error) {
    locationsError.value = error.message || "Lokace se nepodařilo načíst.";
  } finally {
    locationsStatus.value = "ready";
  }
}

function handleFiltersUpdate(nextFilters) {
  filters.favorites = normalizeFilterValues(nextFilters.favorites);
  filters.subcategories = normalizeFilterValues(nextFilters.subcategories);
  filters.statuses = normalizeFilterValues(nextFilters.statuses);
  filters.ratings = normalizeFilterValues(nextFilters.ratings);
  filters.accessibilities = normalizeFilterValues(nextFilters.accessibilities);
}

function handleMapCreateLocation(coordinates) {
  editorError.value = "";
  selectedLocationId.value = null;
  editorMode.value = "create";
  editorLocation.value = {
    title: "",
    latitude: Number(coordinates.latitude.toFixed(6)),
    longitude: Number(coordinates.longitude.toFixed(6)),
    category: "other",
    subcategory: "other",
    status: "unsorted",
    rating: "unrated",
    accessibility: "unknown",
  };
}

async function handleLocationSave(payload) {
  editorError.value = "";
  isEditorSubmitting.value = true;
  try {
    const response =
      editorMode.value === "edit" && editorLocation.value?.id
        ? await updateLocation(editorLocation.value.id, payload)
        : await createLocation(payload);

    const nextLocation = {
      ...response.location,
      photos: locations.value.find((location) => location.id === response.location.id)?.photos || [],
    };

    if (editorMode.value === "edit") {
      locations.value = locations.value.map((location) =>
        location.id === response.location.id ? nextLocation : location,
      );
    } else {
      locations.value = [...locations.value, { ...response.location, photos: [] }];
    }

    selectedLocationId.value = response.location.id;
    closeLocationEditor();
  } catch (error) {
    editorError.value = error.message || "Lokaci se nepodařilo uložit.";
  } finally {
    isEditorSubmitting.value = false;
  }
}

function handleMapEditLocation(locationId) {
  const location = locations.value.find((item) => item.id === locationId);
  if (!location) {
    locationsError.value = "Lokace se nepodařilo najít.";
    return;
  }

  editorError.value = "";
  selectedLocationId.value = location.id;
  editorMode.value = "edit";
  editorLocation.value = { ...location };
}

async function handleMapDeleteLocation(locationId) {
  const location = locations.value.find((item) => item.id === locationId);
  if (!location) {
    locationsError.value = "Lokace se nepodařilo najít.";
    return;
  }
  if (!window.confirm(`Opravdu smazat lokaci „${location.title}“?`)) {
    return;
  }

  locationsError.value = "";
  try {
    await deleteLocation(location.id);
    locations.value = locations.value.filter((item) => item.id !== location.id);
    if (selectedLocationId.value === location.id) {
      selectedLocationId.value = null;
    }
    if (editorLocation.value?.id === location.id) {
      closeLocationEditor();
    }
  } catch (error) {
    locationsError.value = error.message || "Lokaci se nepodařilo smazat.";
  }
}

async function handleToggleFavorite(payload) {
  locationsError.value = "";
  try {
    const response = await setLocationFavorite(payload.locationId, payload.isFavorite);
    locations.value = locations.value.map((location) =>
      location.id === response.location.id ? { ...response.location, photos: location.photos || [] } : location,
    );
  } catch (error) {
    locationsError.value = error.message || "Oblíbenou lokaci se nepodařilo změnit.";
  }
}

async function handleUploadPhoto(payload) {
  locationsError.value = "";
  try {
    const response = await uploadLocationPhoto(payload.locationId, payload.file);
    locations.value = locations.value.map((location) =>
      location.id === payload.locationId
        ? { ...location, photos: [response.photo, ...(location.photos || [])] }
        : location,
    );
  } catch (error) {
    locationsError.value = error.message || "Fotku se nepodařilo nahrát.";
  }
}

async function handleDeletePhoto(payload) {
  const location = locations.value.find((item) => item.id === payload.locationId);
  const photo = location?.photos?.find((item) => item.id === payload.photoId);
  if (!photo) {
    locationsError.value = "Fotku se nepodařilo najít.";
    return;
  }
  if (!window.confirm(`Opravdu smazat fotku „${photo.original_filename}“?`)) {
    return;
  }

  locationsError.value = "";
  try {
    await deleteLocationPhoto(payload.locationId, payload.photoId);
    locations.value = locations.value.map((item) =>
      item.id === payload.locationId
        ? { ...item, photos: (item.photos || []).filter((candidate) => candidate.id !== payload.photoId) }
        : item,
    );
  } catch (error) {
    locationsError.value = error.message || "Fotku se nepodařilo smazat.";
  }
}

function closeLocationEditor() {
  editorMode.value = "";
  editorLocation.value = null;
  editorError.value = "";
}

function resetFilters() {
  const defaultValues = createDefaultFilters();
  filters.favorites = defaultValues.favorites;
  filters.subcategories = defaultValues.subcategories;
  filters.statuses = defaultValues.statuses;
  filters.ratings = defaultValues.ratings;
  filters.accessibilities = defaultValues.accessibilities;
}

function createDefaultFilters() {
  return {
    favorites: [...defaultFilters.favorites],
    subcategories: [...defaultFilters.subcategories],
    statuses: [...defaultFilters.statuses],
    ratings: [...defaultFilters.ratings],
    accessibilities: [...defaultFilters.accessibilities],
  };
}

async function attachPhotos(locationItems) {
  return Promise.all(
    locationItems.map(async (location) => {
      try {
        const payload = await listLocationPhotos(location.id);
        return { ...location, photos: payload.photos || [] };
      } catch {
        return { ...location, photos: [] };
      }
    }),
  );
}

function normalizeFilterValues(values) {
  return Array.isArray(values) ? [...values] : [];
}

function matchesSelected(selectedValues, actualValue) {
  return selectedValues.includes(actualValue);
}
</script>

<template>
  <main class="app-shell">
    <header v-if="currentUser" class="topbar">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true"></span>
        <h1>Databáze objektů k fotografování</h1>
      </div>
      <div class="topbar__actions">
        <div class="base-layer-switch" role="group" aria-label="Výběr podkladové mapy">
          <button
            v-for="option in baseLayerOptions"
            :key="option.value"
            class="base-layer-switch__option"
            :class="{ 'base-layer-switch__option--active': selectedBaseLayer === option.value }"
            type="button"
            :title="option.title"
            @click="selectedBaseLayer = option.value"
          >
            {{ option.label }}
          </button>
        </div>
        <button class="ghost-button ghost-button--compact" type="button" @click="isChangePasswordOpen = true">
          Změnit heslo
        </button>
        <button class="ghost-button ghost-button--compact" type="button" :disabled="isSubmitting" @click="handleLogout">
          Odhlásit
        </button>
      </div>
    </header>
    <div v-if="currentUser" class="map-workspace">
      <MapView
        :locations="filteredLocations"
        :selected-location-id="selectedLocationId"
        :draft-location="editorMode === 'create' ? editorLocation : null"
        :base-layer="selectedBaseLayer"
        @select-location="selectedLocationId = $event"
        @create-location="handleMapCreateLocation"
        @toggle-favorite="handleToggleFavorite"
        @edit-location="handleMapEditLocation"
        @delete-location="handleMapDeleteLocation"
        @upload-photo="handleUploadPhoto"
        @delete-photo="handleDeletePhoto"
        @location-popup-open-change="isLocationPopupOpen = $event"
      />
      <button
        class="filter-side-toggle"
        :class="{
          'filter-side-toggle--open': isFilterPanelOpen,
          'filter-side-toggle--active': activeFilterCount > 0,
          'filter-side-toggle--covered': isLocationPopupOpen,
        }"
        type="button"
        aria-controls="location-filter-panel"
        :aria-expanded="isFilterPanelOpen"
        :aria-label="isFilterPanelOpen ? 'Skrýt filtry' : 'Zobrazit filtry'"
        @click="isFilterPanelOpen = !isFilterPanelOpen"
      >
        <span class="filter-side-toggle__chevron" aria-hidden="true"></span>
        <span v-if="activeFilterCount > 0" class="filter-side-toggle__count">{{ activeFilterCount }}</span>
      </button>
      <p v-if="locationsError || locationsStatus === 'loading'" class="map-message" :class="{ 'map-message--error': locationsError }">
        {{ locationsError || "Načítám lokace..." }}
      </p>
      <LocationFilters
        :filters="filters"
        :favorite-options="favoriteOptions"
        :is-open="isFilterPanelOpen"
        :total-count="locations.length"
        :visible-count="filteredLocations.length"
        @update:filters="handleFiltersUpdate"
        @reset="resetFilters"
        @close="isFilterPanelOpen = false"
      />
      <div v-if="editorMode" class="location-editor-layer">
        <LocationFormPanel
          :mode="editorMode"
          :location="editorLocation"
          :error="editorError"
          :is-submitting="isEditorSubmitting"
          @save="handleLocationSave"
          @close="closeLocationEditor"
        />
      </div>
      
      <ChangePasswordPanel
        v-if="isChangePasswordOpen"
        @close="isChangePasswordOpen = false"
      />
    </div>

    <div v-else class="auth-screen">
      <AuthPanel
        :error="authError"
        :is-busy="isAuthBusy"
        :is-submitting="isSubmitting"
        @login="handleLogin"
        @register="handleRegister"
      />
      <p v-if="isSubmitting" class="auth-message">Zpracovávám...</p>
      <p v-else-if="authStatus === 'checking'" class="auth-message">Kontroluji přihlášení...</p>
      <p v-else-if="authError" class="auth-message auth-message--error">{{ authError }}</p>
    </div>
  </main>
</template>
