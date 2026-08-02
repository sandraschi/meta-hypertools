import { test } from "@playwright/test";
import path from "path";
import config from "./config.json";

const OUT_DIR = path.resolve(__dirname, config.output_dir || "../../docs/screenshots");

test.describe("Video walkthrough", () => {
  test.use({ video: "on" });

  test(config.video_name || "full walkthrough", async ({ page, context }) => {
    await context.tracing.start({ screenshots: true, snapshots: true });

    for (const step of config.video_steps) {
      switch (step.action) {
        case "goto":
          await page.goto(step.url);
          break;
        case "wait":
          await page.waitForTimeout(step.ms || 1000);
          break;
        case "wait_selector":
          await page.waitForSelector(step.selector, { timeout: step.timeout || 15000 });
          break;
        case "click": {
          const btn = page.locator(step.selector);
          if (await btn.isVisible()) await btn.click();
          break;
        }
        case "fill": {
          const input = page.locator(step.selector);
          if (await input.isVisible()) await input.fill(step.value);
          break;
        }
      }
    }

    await context.tracing.stop({ path: path.join(OUT_DIR, config.trace_name || "demo-trace.zip") });
  });
});
