import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // Not "assets": Cloudflare edge sometimes immutable-caches SPA HTML for missing
    // /assets/* hashes after a deploy race (custom domain). A distinct dir busts that.
    assetsDir: "static",
    modulePreload: {
      resolveDependencies(filename, deps) {
        return deps.filter((dep) => !dep.includes("icons"));
      },
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (
            id.includes(`${"node_modules"}/react-dom`) ||
            id.includes(`${"node_modules"}/react-router`) ||
            id.includes(`${"node_modules"}/scheduler`) ||
            /node_modules\/react\//.test(id)
          ) {
            return "react-vendor";
          }
          if (id.includes("@tanstack")) {
            return "query";
          }
          if (id.includes("lucide-react")) {
            return "icons";
          }
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Tunnels and custom domains hit Vite with their own Host header
    // true = allow any Host header in local dev (do not use for public untrusted hosts)
    allowedHosts: true,
    proxy: {
      "/api": {
        // Docker Compose exposes the API on 3001; some local uvicorn runs use 3002.
        target: process.env.VITE_DEV_API_PROXY || "http://localhost:3001",
        changeOrigin: true,
        // Required for render-queue live WS (/api/ws/renders) via Vite (and Cloudflare tunnels).
        ws: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
    allowedHosts: true,
  },
});
