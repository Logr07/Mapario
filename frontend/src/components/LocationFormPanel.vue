<script setup>
import { computed, reactive, ref, watch } from "vue";

import {
  accessibilityOptions,
  categoryOptions,
  ratingOptions,
  statusOptions,
  subcategoriesForCategory,
} from "../utils/locationStructure";
import { formatDecimalCoordinates, parseCoordinates } from "../utils/coordinates";

const props = defineProps({
  mode: {
    type: String,
    required: true,
  },
  location: {
    type: Object,
    default: null,
  },
  error: {
    type: String,
    default: "",
  },
  isSubmitting: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["save", "close"]);

const form = reactive({
  title: "",
  coordinates: "",
  category: "other",
  subcategory: "other",
  status: "unsorted",
  rating: "unrated",
  accessibility: "unknown",
});
const localError = ref("");

const panelTitle = computed(() => (props.mode === "edit" ? "Upravit lokaci" : "Nová lokace"));
const submitLabel = computed(() => (props.mode === "edit" ? "Uložit změny" : "Vytvořit lokaci"));
const availableSubcategoryOptions = computed(() => subcategoriesForCategory(form.category));

watch(
  () => props.location,
  (location) => {
    localError.value = "";
    form.title = location?.title || "";
    form.coordinates =
      location?.latitude != null && location?.longitude != null
        ? formatDecimalCoordinates(location.latitude, location.longitude)
        : "";
    form.category = location?.category || "other";
    form.subcategory = location?.subcategory || subcategoriesForCategory(form.category)[0].value;
    form.status = location?.status || "unsorted";
    form.rating = location?.rating || "unrated";
    form.accessibility = location?.accessibility || "unknown";
  },
  { immediate: true },
);

function submitForm() {
  localError.value = "";

  if (!form.title.trim()) {
    localError.value = "Popis lokace je povinný.";
    return;
  }
  const coordinates = parseCoordinates(form.coordinates);
  if (!coordinates) {
    localError.value = "Souřadnice nejsou v podporovaném formátu.";
    return;
  }

  emit("save", {
    title: form.title.trim(),
    latitude: coordinates.latitude,
    longitude: coordinates.longitude,
    category: form.category,
    subcategory: form.subcategory,
    status: form.status,
    rating: form.rating,
    accessibility: form.accessibility,
  });
}

function handleCategoryChange() {
  const subcategories = subcategoriesForCategory(form.category);
  if (!subcategories.some((option) => option.value === form.subcategory)) {
    form.subcategory = subcategories[0].value;
  }
}
</script>

<template>
  <aside class="location-editor" role="dialog" aria-modal="true" aria-label="Formulář lokace">
    <div class="panel-header">
      <div>
        <p class="panel-kicker">Správa lokace</p>
        <h2>{{ panelTitle }}</h2>
      </div>
      <button class="icon-button" type="button" title="Zavřít formulář" @click="$emit('close')">×</button>
    </div>

    <form class="location-form" @submit.prevent="submitForm">
      <p v-if="localError || error" class="panel-error">{{ localError || error }}</p>

      <label>
        Popis
        <textarea v-model="form.title" class="location-form__main-text" rows="3" maxlength="180" wrap="soft" required></textarea>
      </label>

      <label>
        Kategorie
        <select v-model="form.category" @change="handleCategoryChange">
          <option v-for="option in categoryOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label>
        Podtyp
        <select v-model="form.subcategory">
          <option v-for="option in availableSubcategoryOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <div class="form-grid">
        <label>
          Stav
          <select v-model="form.status">
            <option v-for="option in statusOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <label>
          Hodnocení
          <select v-model="form.rating">
            <option v-for="option in ratingOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>

      <label>
        Přístupnost
        <select v-model="form.accessibility">
          <option v-for="option in accessibilityOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label>
        Souřadnice
        <input v-model="form.coordinates" type="text" inputmode="text" placeholder="50.087799, 14.450885" required />
      </label>

      <div class="form-actions">
        <button class="ghost-button" type="button" @click="$emit('close')">Zrušit</button>
        <button class="primary-button" type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? "Ukládám..." : submitLabel }}
        </button>
      </div>
    </form>
  </aside>
</template>
