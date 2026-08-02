export type FleetStdioSmokeResult = {
  clientId?: string;
  client?: string;
  serverName?: string;
  command?: string;
  ok?: boolean;
  error?: string;
};

export type FleetColdInstallRow = {
  repo: string;
  outcome: string;
  mcpbOutcome?: string;
  stdioOutcome?: string;
  stdioSmokeResults?: FleetStdioSmokeResult[];
  primaryOption?: string;
  installPath?: string;
  mcpbConfigEntry?: string;
  errorMessage?: string;
  logExcerpt?: string;
  durationSec?: number;
};

export type FleetColdInstallComparison = {
  priorGeneratedAt?: string;
  probeMode?: string;
  reposProbed?: number;
  install_failed_prior?: number;
  install_failed_now?: number;
  install_failed_delta?: number;
  mcpb_ok_prior?: number;
  mcpb_ok_now?: number;
  mcpb_ok_delta?: number;
};

export type FleetColdInstallExportMeta = {
  status: string;
  generatedAt?: string;
  completed?: number;
  totalExpected?: number;
  summary?: Record<string, number>;
  comparison?: FleetColdInstallComparison | null;
  filterLabel?: string;
};

function escapeCsv(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

export function buildColdInstallCsv(rows: FleetColdInstallRow[]): string {
  const headers = [
    "repo",
    "outcome",
    "mcpb_outcome",
    "stdio_outcome",
    "stdio_clients",
    "primary_option",
    "install_path",
    "mcpb_config_entry",
    "error_message",
    "duration_sec",
    "log_excerpt",
  ];
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(
      [
        row.repo,
        row.outcome,
        row.mcpbOutcome ?? "",
        row.stdioOutcome ?? "",
        row.stdioSmokeResults?.map((s) => `${s.client}:${s.ok ? "ok" : "fail"}`).join("; ") ?? "",
        row.primaryOption ?? "",
        row.installPath ?? "",
        row.mcpbConfigEntry ?? "",
        row.errorMessage ?? "",
        row.durationSec != null ? String(row.durationSec) : "",
        row.logExcerpt ?? "",
      ]
        .map((cell) => escapeCsv(cell))
        .join(","),
    );
  }
  return `${lines.join("\n")}\n`;
}

export function buildColdInstallMarkdown(
  rows: FleetColdInstallRow[],
  meta: FleetColdInstallExportMeta,
): string {
  const lines: string[] = [];
  lines.push("# Fleet cold-install probe export");
  lines.push("");
  lines.push(`Status: ${meta.status}`);
  if (meta.generatedAt) lines.push(`Generated: ${meta.generatedAt}`);
  if (meta.filterLabel) lines.push(`Filter: ${meta.filterLabel}`);
  if (meta.comparison) {
    const c = meta.comparison;
    const d = c.install_failed_delta ?? 0;
    const dl = d > 0 ? `+${d}` : String(d);
    lines.push(
      `Install/doc failures: ${c.install_failed_now ?? "?"} (was ${c.install_failed_prior ?? "?"}, ${dl})`,
    );
    if ((c.mcpb_ok_now ?? 0) > 0 || (c.mcpb_ok_prior ?? 0) > 0) {
      lines.push(`mcpb ok: ${c.mcpb_ok_now ?? 0} (was ${c.mcpb_ok_prior ?? 0})`);
    }
  }
  lines.push("");
  if (meta.summary) {
    lines.push("## Summary");
    lines.push("");
    lines.push("| Metric | Count |");
    lines.push("| --- | ---: |");
    for (const [k, v] of Object.entries(meta.summary)) {
      lines.push(`| ${k} | ${v} |`);
    }
    lines.push("");
  }
  lines.push("## Results");
  lines.push("");
  lines.push("| Repo | Outcome | mcpb | Option | Error |");
  lines.push("| --- | --- | --- | --- | --- |");
  for (const row of rows) {
    const err = (row.errorMessage ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ");
    lines.push(
      `| ${row.repo} | ${row.outcome} | ${row.mcpbOutcome ?? "-"} | ${row.primaryOption ?? "-"} | ${err || "-"} |`,
    );
  }
  for (const row of rows) {
    if (!row.logExcerpt) continue;
    lines.push("");
    lines.push(`### ${row.repo}`);
    lines.push("```text");
    lines.push(row.logExcerpt);
    lines.push("```");
  }
  return `${lines.join("\n")}\n`;
}

export function coldInstallExportFilename(ext: "md" | "csv"): string {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  return `fleet-cold-install-export-${stamp}.${ext}`;
}

export function downloadTextFile(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
