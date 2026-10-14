import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  use: { baseURL: process.env.BASE_URL ?? "http://localhost:5173", viewport: { width: 1440, height: 900 } },
  reporter: "line",
});
