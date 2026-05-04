import { apiRequest } from "./client";

export function searchAddress(query, options = {}) {
  const params = new URLSearchParams({ query });
  return apiRequest(`/geocode?${params.toString()}`, {
    timeoutMs: 12000,
    ...options,
  });
}

export function suggestAddresses(query, options = {}) {
  const params = new URLSearchParams({ query });
  return apiRequest(`/geocode/suggest?${params.toString()}`, {
    timeoutMs: 12000,
    ...options,
  });
}
