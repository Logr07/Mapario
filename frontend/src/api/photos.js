import { apiRequest } from "./client";

export function listLocationPhotos(locationId) {
  return apiRequest(`/locations/${locationId}/photos`);
}

export function uploadLocationPhoto(locationId, file) {
  const formData = new FormData();
  formData.append("photo", file);

  return apiRequest(`/locations/${locationId}/photos`, {
    method: "POST",
    body: formData,
    timeoutMs: 60000,
  });
}

export function deleteLocationPhoto(locationId, photoId) {
  return apiRequest(`/locations/${locationId}/photos/${photoId}`, {
    method: "DELETE",
  });
}
