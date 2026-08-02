import type { FleetProbeRow } from "./fleetProbeExport";

export type FleetBadgeKind =
  | "healthy"
  | "offline"
  | "404"
  | "500"
  | "unavailable"
  | "parse"
  | "backend"
  | "frontend"
  | "proxy"
  | "teardown"
  | "down";

export type FleetBadge = {
  kind: FleetBadgeKind;
  label: string;
  title?: string;
};

export type RuntimeBadgeApp = {
  status: string;
  health_code?: number | null;
  error?: string;
};

export const FLEET_PROBLEM_BADGES: FleetBadgeKind[] = ["offline", "404", "500", "unavailable"];

export function deriveRuntimeBadges(app: RuntimeBadgeApp): FleetBadge[] {
  const badges: FleetBadge[] = [];
  if (app.status === "offline") {
    badges.push({ kind: "offline", label: "offline" });
    return badges;
  }
  if (app.status === "healthy") {
    badges.push({ kind: "healthy", label: "healthy" });
    return badges;
  }
  const code = app.health_code ?? null;
  if (code === 404) {
    badges.push({ kind: "404", label: "404", title: app.error });
  } else if (code != null && code >= 500) {
    badges.push({ kind: "500", label: "500", title: app.error ?? `HTTP ${code}` });
  } else if (code != null && code >= 400) {
    badges.push({ kind: "unavailable", label: "unavailable", title: app.error ?? `HTTP ${code}` });
  } else {
    badges.push({ kind: "unavailable", label: "unavailable", title: app.error });
  }
  return badges;
}

export function deriveProbeBadges(row: FleetProbeRow): FleetBadge[] {
  const badges: FleetBadge[] = [];
  const kinds = new Set<FleetBadgeKind>();

  const push = (badge: FleetBadge) => {
    if (kinds.has(badge.kind)) return;
    kinds.add(badge.kind);
    badges.push(badge);
  };

  if (row.parseOk === false) {
    push({ kind: "parse", label: "parse" });
  }
  if (row.backendOk) {
    push({ kind: "backend", label: "backend" });
  }
  if (row.frontendOk === true) {
    push({ kind: "frontend", label: "frontend" });
  } else if (row.frontendOk === false && row.backendOk) {
    push({ kind: "unavailable", label: "unavailable", title: "Frontend not ready" });
  }
  if (row.proxyOk === true) {
    push({ kind: "proxy", label: "proxy" });
  } else if (row.proxyOk === false && row.backendOk) {
    push({ kind: "unavailable", label: "unavailable", title: "Proxy health failed" });
  }

  for (const pc of row.pageChecks ?? []) {
    if (pc.status === 404) {
      push({ kind: "404", label: "404", title: pc.path });
    } else if (pc.status != null && pc.status >= 500) {
      push({ kind: "500", label: "500", title: `${pc.path} HTTP ${pc.status}` });
    } else if (!pc.ok) {
      push({
        kind: "unavailable",
        label: "unavailable",
        title: pc.path + (pc.status != null ? ` HTTP ${pc.status}` : ""),
      });
    }
  }

  if (row.outcome === "pages_404" && !kinds.has("404")) {
    push({ kind: "404", label: "404", title: row.errorMessage });
  }
  if (row.outcome === "start_failed" && !row.backendOk) {
    push({ kind: "offline", label: "offline", title: row.errorMessage });
  }

  if (row.teardownOk === true) {
    push({ kind: "down", label: "down" });
  } else if (row.teardownOk === false) {
    push({ kind: "teardown", label: "teardown!" });
  }

  return badges;
}

export function runtimeMatchesBadgeFilter(app: RuntimeBadgeApp, filter: string): boolean {
  if (filter === "all") return true;
  const badges = deriveRuntimeBadges(app);
  if (filter === "healthy") return app.status === "healthy";
  if (filter === "deficient") return app.status === "deficient";
  if (filter === "offline") return app.status === "offline";
  return badges.some((b) => b.kind === filter);
}

export function probeMatchesBadgeFilter(row: FleetProbeRow, filter: string): boolean {
  if (filter === "all") return true;
  if (
    [
      "stack_ok",
      "backend_ok",
      "parse_failed",
      "root_order_failed",
      "start_failed",
      "skip",
      "pages_404",
    ].includes(filter)
  ) {
    return row.outcome === filter;
  }
  return deriveProbeBadges(row).some((b) => b.kind === filter);
}

export function countRuntimeBadgeKinds(apps: RuntimeBadgeApp[]): Record<string, number> {
  const counts: Record<string, number> = {
    healthy: 0,
    offline: 0,
    "404": 0,
    "500": 0,
    unavailable: 0,
  };
  for (const app of apps) {
    if (app.status === "healthy") {
      counts.healthy += 1;
      continue;
    }
    if (app.status === "offline") {
      counts.offline += 1;
      continue;
    }
    const code = app.health_code ?? null;
    if (code === 404) counts["404"] += 1;
    else if (code != null && code >= 500) counts["500"] += 1;
    else counts.unavailable += 1;
  }
  return counts;
}

export function countProbeBadgeKinds(rows: FleetProbeRow[]): Record<string, number> {
  const counts: Record<string, number> = {
    "404": 0,
    "500": 0,
    offline: 0,
    unavailable: 0,
    stack_ok: 0,
  };
  for (const row of rows) {
    if (row.outcome === "stack_ok") counts.stack_ok += 1;
    const kinds = new Set(deriveProbeBadges(row).map((b) => b.kind));
    for (const kind of kinds) {
      if (kind in counts) counts[kind] += 1;
    }
  }
  return counts;
}
