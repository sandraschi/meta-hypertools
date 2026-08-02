import react from "@vitejs/plugin-react";
/// <reference types="vitest" />
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig(<any>{
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    exclude: ["e2e/**", "node_modules/**"],
  },
  server: {
    allowedHosts: ['goliath'],
    port: 10719,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://localhost:10718",
        changeOrigin: true,
        secure: false,
      },
      "/mcp": {
        target: "http://localhost:10718",
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
