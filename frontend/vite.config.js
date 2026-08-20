import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/nodos": "http://localhost:8000",
      "/relations": "http://localhost:8000",
      "/ingesta": "http://localhost:8000",
    },
  },
});
