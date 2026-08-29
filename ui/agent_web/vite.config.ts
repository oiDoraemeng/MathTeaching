import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  plugins: [react() as any],
  build: {
    manifest: "manifest.json",
    assetsDir: "assets",
    rollupOptions: {
      input: "./index.html",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/testSetup.ts",
    exclude: ["scripts/**/*.test.mjs", "node_modules/**", "dist/**"],
  },
});
