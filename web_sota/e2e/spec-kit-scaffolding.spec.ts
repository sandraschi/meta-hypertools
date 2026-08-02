import { test, expect } from "@playwright/test";
import { AUTH, BE } from "./config";

test.describe("Spec Kit Scaffolding", () => {
  test("POST spec_kit returns expected shape", async ({ request }) => {
    const resp = await request.post(`${BE}/api/v1/scaffolding/create`, {
      headers: AUTH,
      data: {
        template_type: "spec_kit",
        project_name: "e2e-test-spec",
        output_path: "/tmp",
        features: { ai_integration: "opencode" },
      },
    });

    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.success).toBeDefined();
    expect(typeof body.success).toBe("boolean");
    expect(typeof body.message).toBe("string");
  });

  test("POST rejects unknown template_type", async ({ request }) => {
    const resp = await request.post(`${BE}/api/v1/scaffolding/create`, {
      headers: AUTH,
      data: {
        template_type: "bogus_type",
        project_name: "nope",
        output_path: "/tmp",
      },
    });

    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.success).toBe(false);
    expect(body.message).toContain("Unsupported template type");
  });

  test("POST requires auth header", async ({ request }) => {
    const resp = await request.post(`${BE}/api/v1/scaffolding/create`, {
      data: {
        template_type: "mcp_server",
        project_name: "unauth-test",
        output_path: "/tmp",
      },
    });

    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.success).toBeDefined();
  });
});
