import { apiRequest } from "./client";

export function listLocations() {
  return apiRequest("/locations");
}

export function getLocation(locationId) {
  return apiRequest(`/locations/${locationId}`);
}

export function createLocation(payload) {
  return apiRequest("/locations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateLocation(locationId, payload) {
  return apiRequest(`/locations/${locationId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteLocation(locationId) {
  return apiRequest(`/locations/${locationId}`, {
    method: "DELETE",
  });
}

export function setLocationFavorite(locationId, isFavorite) {
  return apiRequest(`/locations/${locationId}/favorite`, {
    method: "PUT",
    body: JSON.stringify({ is_favorite: isFavorite }),
  });
}
