import { apiRequest } from "./client";

export function getCurrentUser(options = {}) {
  return apiRequest("/auth/me", options);
}

export function registerUser(payload) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginUser(payload) {
  return apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function logoutUser() {
  return apiRequest("/auth/logout", {
    method: "POST",
  });
}

export function changePassword(payload) {
  return apiRequest("/auth/change-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
