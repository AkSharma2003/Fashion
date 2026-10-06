import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: ["cggv4t8c-5173.inc1.devtunnels.ms"],
  },
});