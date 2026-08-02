# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: screenshots.spec.ts >> Screenshots >> Page scrubbers
- Location: e2e\screenshots.spec.ts:40:5

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:10719/
Call log:
  - navigating to "http://127.0.0.1:10719/", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | import { BE } from "./config";
  3  | 
  4  | const FE = "http://127.0.0.1:10719";
  5  | 
  6  | const FUNCTIONAL_PAGES = [
  7  |   { id: "dashboard", navLabel: "Dashboard" },
  8  |   { id: "apps", navLabel: "Apps Hub" },
  9  |   { id: "fleet", navLabel: "Fleet Status" },
  10 |   { id: "agent-hub", navLabel: "Fritz / RoboFang" },
  11 |   { id: "chat", navLabel: "Chat" },
  12 |   { id: "servers", navLabel: "Server Registry" },
  13 |   { id: "clients", navLabel: "Clients" },
  14 |   { id: "toolchains", navLabel: "Toolchains" },
  15 |   { id: "builders", navLabel: "Builders" },
  16 |   { id: "tools", navLabel: "Tools" },
  17 |   { id: "harness", navLabel: "Harness Generator" },
  18 |   { id: "tool-lab", navLabel: "Tool Sandbox" },
  19 |   { id: "tauri-build", navLabel: "Tauri Build" },
  20 |   { id: "repo-inspiration", navLabel: "Repo Inspiration" },
  21 |   { id: "analysis", navLabel: "Analysis" },
  22 |   { id: "config-audit", navLabel: "Config Audit" },
  23 |   { id: "scrubbers", navLabel: "Scrubbers" },
  24 | ];
  25 | 
  26 | test.describe("Screenshots", () => {
  27 |   test("Backend health", async ({ request }) => {
  28 |     const resp = await request.get(`${BE}/health`);
  29 |     expect(resp.status()).toBe(200);
  30 |   });
  31 | 
  32 |   test("Sidebar expanded", async ({ page }) => {
  33 |     await page.setViewportSize({ width: 1280, height: 720 });
  34 |     await page.goto(FE, { timeout: 15000 });
  35 |     await page.waitForTimeout(3000);
  36 |     await page.screenshot({ path: "docs/screenshots/sidebar.png", fullPage: false });
  37 |   });
  38 | 
  39 |   for (const pg of FUNCTIONAL_PAGES) {
  40 |     test(`Page ${pg.id}`, async ({ page }) => {
  41 |       await page.setViewportSize({ width: 1280, height: 720 });
> 42 |       await page.goto(FE, { timeout: 15000 });
     |                  ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:10719/
  43 |       await page.waitForTimeout(2000);
  44 | 
  45 |       // Navigate (collapsed sidebar buttons are always visible)
  46 |       const navBtn = page.locator("button", { hasText: pg.navLabel });
  47 |       if (await navBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
  48 |         await navBtn.click();
  49 |         await page.waitForTimeout(2000);
  50 |       }
  51 | 
  52 |       // Collapse sidebar
  53 |       await page.locator('button[title="Collapse"]').click();
  54 |       await page.waitForTimeout(500);
  55 | 
  56 |       await page.screenshot({ path: `docs/screenshots/${pg.id}.png`, fullPage: true });
  57 |     });
  58 |   }
  59 | });
  60 | 
```