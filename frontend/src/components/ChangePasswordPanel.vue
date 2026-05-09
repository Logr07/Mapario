<script setup>
import { reactive, ref } from "vue";
import { changePassword } from "../api/auth";
import PasswordField from "./PasswordField.vue";

const emit = defineEmits(["close"]);

const form = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const isSubmitting = ref(false);
const error = ref("");
const success = ref(false);

async function submit() {
  if (isSubmitting.value) return;

  error.value = "";
  if (form.newPassword !== form.confirmPassword) {
    error.value = "Nová hesla se neshodují.";
    return;
  }

  isSubmitting.value = true;
  try {
    await changePassword({
      old_password: form.oldPassword,
      new_password: form.newPassword,
    });
    success.value = true;
    setTimeout(() => {
      emit("close");
    }, 2000);
  } catch (err) {
    error.value = err.message || "Změna hesla se nezdařila.";
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-panel">
      <div class="panel-header">
        <h2>Změnit heslo</h2>
        <button class="ghost-button modal-close" type="button" @click="$emit('close')">×</button>
      </div>

      <div v-if="success" class="modal-success">
        <p>Heslo bylo úspěšně změněno.</p>
      </div>
      
      <form v-else class="modal-form" @submit.prevent="submit">
        <PasswordField
          id="change-password-current"
          v-model="form.oldPassword"
          label="Současné heslo"
          autocomplete="current-password"
          :disabled="isSubmitting"
          required
        />
        
        <PasswordField
          id="change-password-new"
          v-model="form.newPassword"
          label="Nové heslo"
          autocomplete="new-password"
          :disabled="isSubmitting"
          required
          minlength="8"
        />
        
        <PasswordField
          id="change-password-confirm"
          v-model="form.confirmPassword"
          label="Potvrzení nového hesla"
          autocomplete="new-password"
          :disabled="isSubmitting"
          required
          minlength="8"
        />

        <p v-if="error" class="panel-error">{{ error }}</p>

        <div class="form-actions">
          <button class="ghost-button" type="button" :disabled="isSubmitting" @click="$emit('close')">Zrušit</button>
          <button class="primary-button" type="submit" :disabled="isSubmitting">Uložit nové heslo</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  padding: 16px;
}

.modal-panel {
  width: min(400px, 100%);
  padding: 20px;
  background: var(--color-surface);
  backdrop-filter: blur(16px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-ui);
  color: var(--color-text);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.modal-close {
  padding: 0 8px;
  font-size: 1.5rem;
  line-height: 1;
}

.modal-form {
  display: grid;
  gap: 16px;
}

.modal-form :deep(.input-group) {
  display: grid;
  gap: 6px;
}

.modal-form :deep(.input-label) {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-muted);
}

.modal-form :deep(.password-field__input) {
  width: 100%;
  min-height: 40px;
  padding: 10px 48px 10px 12px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-ui);
  color: var(--color-text);
  outline: none;
}

.modal-form :deep(.password-field__input:focus) {
  border-color: var(--color-primary);
}

.modal-form :deep(.password-field__input:disabled) {
  cursor: not-allowed;
  opacity: 0.6;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.panel-error {
  margin: 0;
  color: var(--color-danger);
  font-size: 0.9rem;
}

.modal-success {
  text-align: center;
  padding: 2rem 0;
  color: var(--color-primary);
  font-weight: bold;
}
</style>
