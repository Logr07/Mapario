<script setup>
import { computed, reactive, ref } from "vue";
import PasswordField from "./PasswordField.vue";

const props = defineProps({
  error: {
    type: String,
    default: "",
  },
  isBusy: {
    type: Boolean,
    default: false,
  },
  isSubmitting: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["login", "register"]);

const mode = ref("login");
const form = reactive({
  email: "",
  password: "",
  confirmPassword: "",
});
const localError = ref("");

const isRegisterMode = computed(() => mode.value === "register");
const submitLabel = computed(() => {
  if (props.isSubmitting) {
    return "Zpracovávám...";
  }
  return isRegisterMode.value ? "Registrovat" : "Přihlásit";
});
const passwordAutocomplete = computed(() => (isRegisterMode.value ? "new-password" : "current-password"));
const switchLabel = computed(() => (isRegisterMode.value ? "Už mám účet" : "Vytvořit účet"));
const displayedError = computed(() => localError.value || props.error);

function submit() {
  if (props.isBusy) {
    return;
  }

  localError.value = "";

  if (isRegisterMode.value && form.password !== form.confirmPassword) {
    localError.value = "Hesla se neshodují.";
    return;
  }

  const payload = {
    email: form.email,
    password: form.password,
  };

  if (isRegisterMode.value) {
    emit("register", payload);
    return;
  }

  emit("login", payload);
}

function switchMode() {
  if (props.isBusy) {
    return;
  }

  localError.value = "";
  form.confirmPassword = "";
  mode.value = isRegisterMode.value ? "login" : "register";
}
</script>

<template>
  <section class="landing-auth" aria-label="Vstup do aplikace">
    <div class="landing-hero">

      <h1 class="fade-in-up" style="animation-delay: 0.1s">
        Databáze objektů <br /><span class="text-gradient">k fotografování</span>
      </h1>
      <p class="landing-subtitle fade-in-up" style="animation-delay: 0.2s">
        Osobní mapová aplikace pro evidenci vizuálně zajímavých míst a budov. Vytvořte si vlastní lokační deník, sdružujte fotodokumentaci a zaznamenávejte atmosféru opuštěných objektů.
      </p>
      
      <div class="landing-features fade-in-up" style="animation-delay: 0.3s" aria-label="Hlavní funkce aplikace">
        <div class="feature-card">
          <div class="feature-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"></polygon><line x1="9" y1="3" x2="9" y2="18"></line><line x1="15" y1="6" x2="15" y2="21"></line></svg>
          </div>
          <div class="feature-content">
            <h3>Interaktivní mapa</h3>
            <p>Přesná lokalizace na mapovém podkladu s možností přepínání vrstev.</p>
          </div>
        </div>
        
        <div class="feature-card">
          <div class="feature-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
          </div>
          <div class="feature-content">
            <h3>Osobní databáze</h3>
            <p>Bezpečné úložiště pro vaše lokality s detailními atributy a stavem.</p>
          </div>
        </div>
        
        <div class="feature-card">
          <div class="feature-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
          </div>
          <div class="feature-content">
            <h3>Fotodokumentace</h3>
            <p>Nahrávejte a spravujte fotografie pro každou navštívenou lokalitu.</p>
          </div>
        </div>
      </div>
    </div>

    <div class="auth-panel-wrapper fade-in-up" style="animation-delay: 0.4s">
      <div class="auth-panel" aria-label="Přihlášení do aplikace">
        <div class="auth-panel-header">
          <p class="auth-panel__eyebrow">{{ isRegisterMode ? "Vítejte na palubě" : "Vítejte zpět" }}</p>
          <h2>{{ isRegisterMode ? "Vytvořit účet" : "Přihlášení" }}</h2>
          <p>Přihlaste se ke své osobní mapě a objevujte dál.</p>
        </div>

        <form class="auth-form" :aria-busy="isBusy" @submit.prevent="submit">
          <label class="input-group">
            <span class="input-label">E-mail</span>
            <input v-model.trim="form.email" type="email" autocomplete="email" :disabled="isBusy" placeholder="např. jan@novak.cz" required />
          </label>



          <PasswordField
            id="auth-password"
            v-model="form.password"
            label="Heslo"
            :autocomplete="passwordAutocomplete"
            :disabled="isBusy"
            placeholder="Minimálně 8 znaků"
            required
            minlength="8"
          />

          <PasswordField
            v-if="isRegisterMode"
            id="auth-confirm-password"
            v-model="form.confirmPassword"
            label="Potvrzení hesla"
            autocomplete="new-password"
            :disabled="isBusy"
            placeholder="Zadejte heslo znovu"
            required
            minlength="8"
          />

          <transition name="fade">
            <p v-if="displayedError" class="auth-panel__error">{{ displayedError }}</p>
          </transition>

          <div class="auth-actions">
            <button class="primary-button action-btn" type="submit" :disabled="isBusy">
              <span v-if="isSubmitting" class="spinner"></span>
              {{ submitLabel }}
            </button>
            <button class="ghost-button link-btn" type="button" :disabled="isBusy" @click="switchMode">{{ switchLabel }}</button>
          </div>
        </form>
      </div>
    </div>
  </section>
  <footer class="auth-footer fade-in-up" style="animation-delay: 0.5s; margin-top: 48px; font-size: 0.8rem; opacity: 0.6; align-self: center; text-align: center;">
    <a href="https://www.flaticon.com/free-icons/information" title="information icons" style="color: inherit; text-decoration: none;">Information icons created by Freepik - Flaticon</a>
  </footer>
</template>
