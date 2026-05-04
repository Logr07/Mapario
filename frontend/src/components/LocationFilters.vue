<script setup>
import { computed, reactive } from "vue";

import {
  accessibilityOptions,
  categoryGroups,
  ratingOptions,
  statusOptions,
  subcategoryOptions,
} from "../utils/locationStructure";

const props = defineProps({
  filters: {
    type: Object,
    required: true,
  },
  isOpen: {
    type: Boolean,
    default: false,
  },
  totalCount: {
    type: Number,
    default: 0,
  },
  visibleCount: {
    type: Number,
    default: 0,
  },
  favoriteOptions: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["update:filters", "reset", "close"]);

const filterGroups = [
  {
    key: "favorites",
    title: "Oblíbené",
    selectAllLabel: "Všechny lokace",
    options: props.favoriteOptions,
  },
  {
    key: "subcategories",
    title: "Podtypy objektů",
    selectAllLabel: "Všechny podtypy",
    options: subcategoryOptions,
  },
  {
    key: "statuses",
    title: "Stav",
    selectAllLabel: "Všechny stavy",
    options: statusOptions,
  },
  {
    key: "ratings",
    title: "Hodnocení",
    selectAllLabel: "Všechna hodnocení",
    options: ratingOptions,
  },
  {
    key: "accessibilities",
    title: "Přístupnost",
    selectAllLabel: "Všechny přístupnosti",
    options: accessibilityOptions,
  },
];

const expandedGroups = reactive({
  favorites: true,
  subcategories: true,
  statuses: true,
  ratings: true,
  accessibilities: true,
});

const expandedSubcategoryCategories = reactive(
  Object.fromEntries(categoryGroups.map((group, index) => [group.value, index === 0])),
);

const excludedFilterCount = computed(() =>
  filterGroups.reduce((count, group) => count + group.options.length - selectedValues(group.key).length, 0),
);

function selectedValues(groupKey) {
  const values = props.filters[groupKey];
  return Array.isArray(values) ? values : [];
}

function emitFilters(groupKey, values) {
  emit("update:filters", {
    subcategories: selectedValues("subcategories"),
    statuses: selectedValues("statuses"),
    ratings: selectedValues("ratings"),
    accessibilities: selectedValues("accessibilities"),
    favorites: selectedValues("favorites"),
    [groupKey]: values,
  });
}

function isChecked(groupKey, value) {
  return selectedValues(groupKey).includes(value);
}

function groupState(group) {
  const selectedCount = selectedValues(group.key).length;
  return {
    checked: selectedCount === group.options.length,
    indeterminate: selectedCount > 0 && selectedCount < group.options.length,
    selectedCount,
  };
}

function toggleGroup(group, checked) {
  emitFilters(
    group.key,
    checked ? group.options.map((option) => option.value) : [],
  );
}

function toggleValue(groupKey, value, checked) {
  const values = new Set(selectedValues(groupKey));
  if (checked) {
    values.add(value);
  } else {
    values.delete(value);
  }

  emitFilters(groupKey, Array.from(values));
}

function subcategoryValues(category) {
  return category.subcategories.map((subcategory) => subcategory.value);
}

function subcategoryCategoryState(category) {
  const selectedSubcategories = selectedValues("subcategories");
  const values = subcategoryValues(category);
  const selectedCount = values.filter((value) => selectedSubcategories.includes(value)).length;

  return {
    checked: selectedCount === values.length,
    indeterminate: selectedCount > 0 && selectedCount < values.length,
    selectedCount,
  };
}

function toggleSubcategoryCategory(category, checked) {
  const values = new Set(selectedValues("subcategories"));

  subcategoryValues(category).forEach((value) => {
    if (checked) {
      values.add(value);
    } else {
      values.delete(value);
    }
  });

  emitFilters("subcategories", Array.from(values));
}
</script>

<template>
  <aside
    id="location-filter-panel"
    class="location-filters"
    :class="{ 'location-filters--open': isOpen }"
    aria-label="Filtry lokalit"
  >
    <div class="panel-header">
      <div>
        <p class="panel-kicker">Filtry lokalit</p>
        <h2>{{ visibleCount }} / {{ totalCount }}</h2>
      </div>
      <div class="filter-header-actions">
        <button class="ghost-button ghost-button--compact" type="button" @click="$emit('reset')">
          Reset
        </button>
        <button class="icon-button" type="button" title="Zavřít filtry" @click="$emit('close')">×</button>
      </div>
    </div>

    <div class="filter-summary">
      <span>{{ excludedFilterCount === 0 ? "Všechny hodnoty povolené" : `${excludedFilterCount} omezení` }}</span>
    </div>

    <div class="filter-groups">
      <section v-for="group in filterGroups" :key="group.key" class="filter-group">
        <button
          class="filter-group__toggle"
          type="button"
          :aria-expanded="expandedGroups[group.key]"
          @click="expandedGroups[group.key] = !expandedGroups[group.key]"
        >
          <span class="filter-group__chevron" aria-hidden="true"></span>
          <span>{{ group.title }}</span>
          <span class="filter-group__count">{{ groupState(group).selectedCount }}/{{ group.options.length }}</span>
        </button>

        <div v-show="expandedGroups[group.key]" class="filter-group__body">
          <label class="filter-check filter-check--parent">
            <input
              type="checkbox"
              :checked="groupState(group).checked"
              :indeterminate="groupState(group).indeterminate"
              @change="toggleGroup(group, $event.target.checked)"
            />
            <span>{{ group.selectAllLabel }}</span>
          </label>

          <div v-if="group.key === 'subcategories'" class="filter-tree">
            <section v-for="category in categoryGroups" :key="category.value" class="filter-tree__group">
              <div class="filter-tree__row">
                <button
                  class="filter-tree__toggle"
                  type="button"
                  :aria-expanded="expandedSubcategoryCategories[category.value]"
                  :aria-label="
                    expandedSubcategoryCategories[category.value]
                      ? `Sbalit ${category.label}`
                      : `Rozbalit ${category.label}`
                  "
                  @click="expandedSubcategoryCategories[category.value] = !expandedSubcategoryCategories[category.value]"
                >
                  <span class="filter-group__chevron" aria-hidden="true"></span>
                </button>

                <label class="filter-check filter-check--tree-parent">
                  <input
                    type="checkbox"
                    :checked="subcategoryCategoryState(category).checked"
                    :indeterminate="subcategoryCategoryState(category).indeterminate"
                    @change="toggleSubcategoryCategory(category, $event.target.checked)"
                  />
                  <span class="filter-check__content">
                    <span>{{ category.label }}</span>
                    <span class="filter-check__count">
                      {{ subcategoryCategoryState(category).selectedCount }}/{{ category.subcategories.length }}
                    </span>
                  </span>
                </label>
              </div>

              <div v-show="expandedSubcategoryCategories[category.value]" class="filter-tree__children">
                <label
                  v-for="option in category.subcategories"
                  :key="option.value"
                  class="filter-check filter-check--tree-child"
                >
                  <input
                    type="checkbox"
                    :checked="isChecked('subcategories', option.value)"
                    @change="toggleValue('subcategories', option.value, $event.target.checked)"
                  />
                  <span>{{ option.label }}</span>
                </label>
              </div>
            </section>
          </div>

          <template v-else>
            <label v-for="option in group.options" :key="option.value" class="filter-check">
              <input
                type="checkbox"
                :checked="isChecked(group.key, option.value)"
                @change="toggleValue(group.key, option.value, $event.target.checked)"
              />
              <span>{{ option.label }}</span>
            </label>
          </template>
        </div>
      </section>
    </div>
  </aside>
</template>
