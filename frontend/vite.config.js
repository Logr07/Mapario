import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

const envBool = (name, defaultValue = false) => {
  const value = process.env[name];
  if (value === undefined) {
    return defaultValue;
  }
  return ["1", "true", "yes", "on"].includes(value.trim().toLowerCase());
};

const allowedHosts = process.env.VITE_ALLOWED_HOSTS
  ? process.env.VITE_ALLOWED_HOSTS.split(",").map((host) => host.trim()).filter(Boolean)
  : true;

const securityHeaders = () => {
  if (!envBool("SECURITY_HEADERS_ENABLED", true)) {
    return {};
  }

  const headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": [
      "default-src 'self'",
      "script-src 'self'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob: https://tile.openstreetmap.org https://*.tile.openstreetmap.org https://*.google.com https://*.gstatic.com",
      "font-src 'self' data:",
      "connect-src 'self' ws: wss:",
      "object-src 'none'",
      "base-uri 'self'",
      "form-action 'self'",
      "frame-ancestors 'none'",
    ].join("; "),
  };

  if (envBool("HSTS_ENABLED", true)) {
    headers["Strict-Transport-Security"] = `max-age=${process.env.HSTS_MAX_AGE || 31536000}; includeSubDomains`;
  }

  return headers;
};

const headers = securityHeaders();

export default defineConfig({
  plugins: [vue()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts,
    headers,
    proxy: {
      "/api": process.env.VITE_API_PROXY_TARGET || "http://localhost:5000",
    },
  },
  preview: {
    headers,
  },
});
