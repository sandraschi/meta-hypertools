import { defineConfig } from "@playwright/test";
import config from "./config.json";

export default defineConfig({
  testDir: ".",
  testMatch: ["demo-screenshots.ts", "demo-video.ts"],
  timeout: 120000,
  retries: 0,
  outputDir: "./demo-test-results",
  use: {
    baseURL: `http://127.0.0.1:${config.frontend_port}`,
    headless: true,
    viewport: { width: 1280, height: 720 },
    screenshot: "only-on-failure",
    video: "on",
    trace: "retain-on-failure",
  },
});
