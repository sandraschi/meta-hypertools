import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HealthStatus, type HealthStatusData } from "./HealthStatus";

describe("HealthStatus", () => {
  it("renders correctly when all services are healthy", () => {
    const mockData: HealthStatusData = {
      healthy: true,
      status: "operational",
      diagnostics: { healthy: true, status: "ok" },
      analysis: { healthy: true, status: "ok" },
      discovery: { healthy: true, status: "ok" },
      scaffolding: { healthy: true, status: "ok" },
    };

    render(<HealthStatus data={mockData} />);

    expect(screen.getByText("Diagnostics")).toBeInTheDocument();
    expect(screen.getAllByText("Operational")).toHaveLength(4);
  });

  it("displays issues when a service is unhealthy", () => {
    const mockData: HealthStatusData = {
      healthy: false,
      status: "degraded",
      diagnostics: { healthy: false, status: "error" },
      analysis: { healthy: true, status: "ok" },
      discovery: { healthy: true, status: "ok" },
      scaffolding: { healthy: true, status: "ok" },
    };

    render(<HealthStatus data={mockData} />);

    expect(screen.getAllByText("Issues Detected")).toHaveLength(1);
    expect(screen.getAllByText("Operational")).toHaveLength(3);
  });
});
