export type FleetProbePageCheck = {
  path: string;
  status?: number | null;
  ok?: boolean;
};

export type FleetProbeComparison = {
  priorGeneratedAt?: string;
  probeMode?: string;
  reposProbed?: number;
  parse_failed_prior?: number;
  parse_failed_now?: number;
  parse_failed_delta?: number;
  root_order_failed_prior?: number;
  root_order_failed_now?: number;
  root_order_failed_delta?: number;
};

export type FleetProbeRow = {
  repo: string;
  outcome: string;
  startPath?: string;
  port?: number;
  parseOk?: boolean | null;
  rootOrderOk?: boolean | null;
  rootOrderLine?: number | null;
  backendOk?: boolean;
  frontendOk?: boolean | null;
  proxyOk?: boolean | null;
  pagesOk?: boolean | null;
  pageChecks?: FleetProbePageCheck[];
  teardownOk?: boolean | null;
  teardownDetail?: string;
  errorMessage?: string;
  logExcerpt?: string;
};

export type FleetProbeExportMeta = {
  status: string;
  generatedAt?: string;
  completed?: number;
  totalExpected?: number;
  summary?: Record<string, number>;
  comparison?: FleetProbeComparison | null;
  filterLabel?: string;
};

function boolLabel(v: boolean | null | undefined): string {
  if (v === true) return "yes";
  if (v === false) return "no";
  return "";
}

function escapeCsv(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

export function buildProbeCsv(rows: FleetProbeRow[]): string {
  const headers = [
    "repo",
    "outcome",
    "parse_ok",
    "backend_ok",
    "frontend_ok",
    "proxy_ok",
    "pages_ok",
    "page_checks",
    "teardown_ok",
    "port",
    "start_path",
    "error_message",
    "teardown_detail",
    "log_excerpt",
  ];
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(
      [
        row.repo,
        row.outcome,
        boolLabel(row.parseOk),
        boolLabel(row.backendOk),
        boolLabel(row.frontendOk),
        boolLabel(row.proxyOk),
        boolLabel(row.pagesOk),
        row.pageChecks?.length
          ? row.pageChecks.map((p) => `${p.path}:${p.status ?? "?"}`).join("; ")
          : "",
        boolLabel(row.teardownOk),
        row.port != null ? String(row.port) : "",
        row.startPath ?? "",
        row.errorMessage ?? "",
        row.teardownDetail ?? "",
        row.logExcerpt ?? "",
      ]
        .map((cell) => escapeCsv(cell))
        .join(","),
    );
  }
  return `${lines.join("\r\n")}\r\n`;
}

export function buildProbeMarkdown(rows: FleetProbeRow[], meta: FleetProbeExportMeta): string {
  const lines: string[] = [
    "# Fleet cold-start probe report",
    "",
    `Generated: ${meta.generatedAt ?? "—"}`,
    `Status: ${meta.status}`,
    `Progress: ${meta.completed ?? rows.length} / ${meta.totalExpected ?? rows.length}`,
  ];
  if (meta.filterLabel) {
    lines.push(`Filter: ${meta.filterLabel}`);
  }
  if (meta.comparison) {
    const c = meta.comparison;
    const pd = c.parse_failed_delta ?? 0;
    const pdLabel = pd > 0 ? `+${pd}` : String(pd);
    lines.push(
      `Parse failures: ${c.parse_failed_now ?? 0} (was ${c.parse_failed_prior ?? 0}, ${pdLabel} since prior run)`,
    );
    if ((c.root_order_failed_now ?? 0) > 0 || (c.root_order_failed_prior ?? 0) > 0) {
      const rd = c.root_order_failed_delta ?? 0;
      const rdLabel = rd > 0 ? `+${rd}` : String(rd);
      lines.push(
        `Root-order failures: ${c.root_order_failed_now ?? 0} (was ${c.root_order_failed_prior ?? 0}, ${rdLabel} since prior run)`,
      );
    }
    if (c.probeMode === "broken_only") {
      lines.push(`Mode: broken_only (${c.reposProbed ?? 0} repos re-probed)`);
    }
  }
  if (meta.summary && Object.keys(meta.summary).length > 0) {
    lines.push("", "## Summary", "");
    lines.push("| Metric | Count |", "| --- | ---: |");
    for (const [key, val] of Object.entries(meta.summary)) {
      lines.push(`| ${key} | ${val} |`);
    }
  }
  lines.push("", "## Results", "");
  if (rows.length === 0) {
    lines.push("_No results._");
    return `${lines.join("\n")}\n`;
  }
  lines.push(
    "| Repo | Outcome | Backend | Frontend | Proxy | Teardown | Error |",
    "| --- | --- | :---: | :---: | :---: | :---: | --- |",
  );
  for (const row of rows) {
    const err = (row.errorMessage ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ");
    lines.push(
      `| ${row.repo} | ${row.outcome} | ${boolLabel(row.backendOk) || "—"} | ${boolLabel(row.frontendOk) || "—"} | ${boolLabel(row.proxyOk) || "—"} | ${boolLabel(row.teardownOk) || "—"} | ${err || "—"} |`,
    );
  }
  for (const row of rows) {
    if (!row.logExcerpt && !row.teardownDetail) continue;
    lines.push("", `### ${row.repo}`, "");
    if (row.teardownDetail) {
      lines.push(`- Teardown: ${row.teardownDetail}`);
    }
    if (row.pageChecks?.length) {
      lines.push(
        `- Pages: ${row.pageChecks
          .map((p) => `${p.path} (${p.ok ? "OK" : `HTTP ${p.status ?? "?"}`})`)
          .join(", ")}`,
      );
    }
    if (row.errorMessage) {
      lines.push(`- Error: ${row.errorMessage}`);
    }
    if (row.logExcerpt) {
      lines.push("", "```text", row.logExcerpt, "```");
    }
  }
  return `${lines.join("\n")}\n`;
}

export function downloadTextFile(content: string, filename: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function probeExportFilename(ext: "csv" | "md", generatedAt?: string): string {
  const stamp = (generatedAt ?? new Date().toISOString()).replace(/[:.]/g, "-").slice(0, 19);
  return `fleet-cold-start-${stamp}.${ext}`;
}
