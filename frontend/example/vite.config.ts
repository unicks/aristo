import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: "dist",
  },
  plugins: [react()],
  server: {
    port: 3003,
  },
  define: {
    APP_VERSION: JSON.stringify(process.env.npm_package_version),
  },
});
