<script setup>
import { computed, ref } from "vue";

defineProps({
  id: {
    type: String,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
  modelValue: {
    type: String,
    default: "",
  },
  autocomplete: {
    type: String,
    default: "",
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  minlength: {
    type: [Number, String],
    default: null,
  },
  placeholder: {
    type: String,
    default: "",
  },
  required: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:modelValue"]);

const isVisible = ref(false);
const inputType = computed(() => (isVisible.value ? "text" : "password"));
const toggleLabel = computed(() => (isVisible.value ? "Skrýt heslo" : "Zobrazit heslo"));

function updateValue(event) {
  emit("update:modelValue", event.target.value);
}

function toggleVisibility() {
  isVisible.value = !isVisible.value;
}
</script>

<template>
  <div class="input-group password-field">
    <label class="input-label" :for="id">{{ label }}</label>
    <span class="password-field__control">
      <input
        :id="id"
        class="password-field__input"
        :value="modelValue"
        :type="inputType"
        :autocomplete="autocomplete || undefined"
        :disabled="disabled"
        :minlength="minlength || undefined"
        :placeholder="placeholder"
        :required="required"
        @input="updateValue"
      />
      <button
        class="password-field__toggle"
        type="button"
        :aria-label="toggleLabel"
        :aria-pressed="isVisible"
        :disabled="disabled"
        :title="toggleLabel"
        @click="toggleVisibility"
      >
        <svg v-if="isVisible" aria-hidden="true" viewBox="0 0 24 24">
          <path d="M3 3l18 18" />
          <path d="M10.7 5.1A10.6 10.6 0 0 1 12 5c5 0 8.7 4 10 7a15.8 15.8 0 0 1-3.1 4.6" />
          <path d="M6.4 6.4A15.3 15.3 0 0 0 2 12c1.3 3 5 7 10 7 1.8 0 3.4-.5 4.8-1.3" />
          <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
        </svg>
        <svg v-else aria-hidden="true" viewBox="0 0 24 24">
          <path d="M2 12s3.7-7 10-7 10 7 10 7-3.7 7-10 7S2 12 2 12Z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </button>
    </span>
  </div>
</template>

<style scoped>
.password-field {
  display: grid;
  gap: 8px;
}

.password-field__control {
  position: relative;
  display: block;
}

.password-field__input {
  padding-right: 52px;
}

.password-field__toggle {
  position: absolute;
  top: 50%;
  right: 6px;
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  padding: 0;
  color: rgba(255, 255, 255, 0.72);
  background: transparent;
  border: 0;
  border-radius: 10px;
  transform: translateY(-50%);
}

.password-field__toggle:hover:not(:disabled) {
  color: var(--color-text);
  background: rgba(255, 255, 255, 0.08);
}

.password-field__toggle:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.password-field__toggle:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.password-field__toggle svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}
</style>
