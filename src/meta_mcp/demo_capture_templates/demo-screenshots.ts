import { test } from "@playwright/test";
import path from "path";
import config from "./config.json";

const OUT_DIR = path.resolve(__dirname, config.output_dir || "../../docs/screenshots");

test.describe("Screenshot capture", () => {
  for (const pageDef of config.pages) {
    test(pageDef.name, async ({ page }) => {
      await page.goto(pageDef.route);
      if (pageDef.selector) await page.waitForSelector(pageDef.selector, { timeout: 15000 });
      const slug = pageDef.name.toLowerCase().replace(/\s+/g, "-");
      await page.screenshot({ path: `${OUT_DIR}/${slug}.png`, fullPage: true });
    });
  }
});
