import { defineConfig } from "@playwright/test";

const BE = "http://127.0.0.1:10699";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  retries: 1,
  use: {
    baseURL: BE,
    headless: true,
    screenshot: "only-on-failure",
    extraHTTPHeaders: {
      "X-Wurst-Auth": "test-wurst-token",
    },
  },
  webServer: [
    {
      command: 'uv run uvicorn meta_mcp.main:app --host 127.0.0.1 --port 10699 --log-level warning',
      url: `${BE}/health`,
      cwd: "../",
      timeout: 30000,
      reuseExistingServer: false,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: 'node "node_modules/.bin/vite" --port 10719',
      url: "http://127.0.0.1:10719",
      cwd: ".",
      timeout: 15000,
      reuseExistingServer: false,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
