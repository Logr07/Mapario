import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import { createApp } from "vue";

import App from "./App.vue";
import "./styles/main.css";

clearLegacyBrowserState();

createApp(App).mount("#app");

/**
 * Odregistruje případné zbytkové Service Workery a smaže jejich cache.
 * Po odregistrování provede jednorazé načtení stránky, aby se klient dostal
 * do čistého stavu (ošetření migrace ze starší verze aplikace).
 */
async function clearLegacyBrowserState() {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  try {
    const hadController = Boolean(navigator.serviceWorker.controller);
    const registrations = await navigator.serviceWorker.getRegistrations();
    const unregistered = await Promise.all(registrations.map((registration) => registration.unregister()));

    if ("caches" in window) {
      const cacheNames = await window.caches.keys();
      await Promise.all(cacheNames.map((cacheName) => window.caches.delete(cacheName)));
    }

    if (
      hadController &&
      unregistered.some(Boolean) &&
      window.sessionStorage.getItem("legacy-service-worker-reload") !== "done"
    ) {
      window.sessionStorage.setItem("legacy-service-worker-reload", "done");
      window.location.reload();
    }
  } catch {
    // Login must keep working even when the browser blocks cache cleanup.
  }
}
