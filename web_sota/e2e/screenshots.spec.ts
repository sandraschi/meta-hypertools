import { test, expect } from "@playwright/test";
import { BE } from "./config";

const FE = "http://127.0.0.1:10719";

const FUNCTIONAL_PAGES = [
  "apps", "fleet", "agent-hub", "chat", "servers", "clients",
  "toolchains", "builders", "tools", "harness", "tool-lab",
  "tauri-build", "repo-inspiration", "analysis", "config-audit", "scrubbers",
];

test.describe("Screenshots", () => {
  test("Backend health", async ({ request }) => {
    const resp = await request.get(`${BE}/health`);
    expect(resp.status()).toBe(200);
  });

  test("Sidebar expanded", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto(FE, { timeout: 20000 });
    await page.waitForTimeout(3000);
    await expect(page.locator("#root")).toBeAttached({ timeout: 10000 });
    await page.screenshot({ path: "docs/screenshots/sidebar.png", fullPage: false });
  });

  test("Dashboard", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto(FE, { timeout: 20000 });
    await page.waitForTimeout(3000);
    await expect(page.locator("#root")).toBeAttached({ timeout: 10000 });
    await page.screenshot({ path: "docs/screenshots/dashboard.png", fullPage: true });
  });

  for (const id of FUNCTIONAL_PAGES) {
    test(`Page ${id}`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 720 });
      await page.goto(FE, { timeout: 20000 });
      await page.waitForTimeout(2000);

      // Navigate via sidebar button
      await page.locator("nav >> button", { hasText: new RegExp(id.replace("-", " "), "i") })
        .click().catch(() => {});
      await page.waitForTimeout(2000);

      await page.screenshot({ path: `docs/screenshots/${id}.png`, fullPage: true });
    });
  }
});
