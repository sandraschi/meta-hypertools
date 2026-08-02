import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Code2,
  FileCode2,
  Loader2,
  RefreshCw,
  Search,
  Server,
  Settings2,
  Terminal,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, getErrorMessage, isSuccessResponse } from "../api/client";

interface Operation {
  name: string;
  signature: string;
  params: { name: string; type?: string; default?: string }[];
  docstring: string | null;
  decorators: string[];
  is_async: boolean;
  is_mutating: boolean;
  source_file: string;
  line_number: number;
}

interface ToolGroup {
  name: string;
  domain: string;
  curated: boolean;
  operation_count: number;
  operations: Operation[];
}

interface ToolSurfaceSpec {
  software_name: string;
  source_type: string;
  source_path: string;
  language: string;
  backend_engine: string;
  state_model: string;
  tool_groups: ToolGroup[];
  warnings: string[];
  total_operations_found: number;
  total_operations_curated: number;
}

interface AnalysisResult {
  spec: ToolSurfaceSpec;
  warnings: string[];
}

interface GenerateResult {
  generated_path: string;
  file_count: number;
  tool_groups: number;
  operations: number;
  backend_engine: string;
}

function StepBadge({ label, active, done }: { label: string; active: boolean; done: boolean }) {
  const bg = done ? "bg-green-600" : active ? "bg-blue-600" : "bg-slate-700";
  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium ${bg} text-white`}
    >
      {done ? (
        <CheckCircle size={14} />
      ) : (
        <span className="w-2 h-2 rounded-full bg-current opacity-60" />
      )}
      {label}
    </div>
  );
}

function DrilledGroup({
  group,
  expanded: initial,
}: {
  group: ToolGroup;
  expanded?: boolean;
}) {
  const [open, setOpen] = useState(initial ?? false);
  const mutCount = group.operations.filter((o) => o.is_mutating).length;
  const roCount = group.operations.length - mutCount;

  return (
    <div className="border border-slate-700 rounded-xl overflow-hidden bg-slate-900/60">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/50 transition-colors text-left"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`p-1.5 rounded-lg ${open ? "bg-blue-500/20 text-blue-400" : "bg-slate-800 text-slate-400"}`}
          >
            {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </div>
          <div>
            <div className="font-semibold text-slate-200">{group.domain}</div>
            <div className="text-xs text-slate-400 font-mono mt-0.5">{group.name}</div>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0 ml-4">
          <div className="text-xs text-slate-400">
            <span className="text-emerald-400 font-medium">{roCount} read</span>
            {mutCount > 0 && (
              <span className="ml-2 text-amber-400 font-medium">{mutCount} write</span>
            )}
          </div>
          <div className="bg-slate-800 text-slate-300 text-sm font-medium px-3 py-1 rounded-lg">
            {group.operation_count}
          </div>
        </div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-4 space-y-2 border-t border-slate-800 pt-3">
              {group.operations.map((op) => (
                <div
                  key={op.name}
                  className="bg-slate-950/60 rounded-lg px-4 py-3 border border-slate-800"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-semibold text-slate-200">
                          {op.name}
                        </span>
                        {op.is_mutating ? (
                          <span className="text-[10px] font-bold text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded uppercase tracking-wider">
                            Write
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded uppercase tracking-wider">
                            Read
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-500 font-mono mt-1 truncate max-w-xl">
                        {op.signature}
                      </div>
                    </div>
                    <div className="text-[10px] text-slate-600 font-mono whitespace-nowrap">
                      {op.source_file}:{op.line_number}
                    </div>
                  </div>
                  {op.docstring && (
                    <div className="mt-2 text-sm text-slate-400 line-clamp-2">{op.docstring}</div>
                  )}
                  {op.params.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {op.params.slice(0, 6).map((p) => (
                        <span
                          key={p.name}
                          className="text-[11px] font-mono bg-slate-800 text-slate-400 px-2 py-0.5 rounded-md"
                        >
                          {p.name}
                          {p.type ? `: ${p.type}` : ""}
                        </span>
                      ))}
                      {op.params.length > 6 && (
                        <span className="text-[11px] text-slate-600">+{op.params.length - 6}</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function HarnessPage() {
  const [step, setStep] = useState<"source" | "results" | "generate" | "done">("source");

  // Analyze inputs
  const [sourcePath, setSourcePath] = useState("");
  const [softwareName, setSoftwareName] = useState("");
  const [fullExtraction, setFullExtraction] = useState(false);

  // Analysis state
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState("");

  // Generate inputs
  const [targetPath, setTargetPath] = useState("");
  const [authorName, setAuthorName] = useState("Harness Generator");
  const [includeNsis, setIncludeNsis] = useState(false);

  // Generate state
  const [generating, setGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState<GenerateResult | null>(null);
  const [generateError, setGenerateError] = useState("");

  // Refine state
  const [refining, setRefining] = useState(false);
  const [refineReport, setRefineReport] = useState<string | null>(null);

  const doAnalyze = useCallback(async () => {
    if (!sourcePath.trim()) return;
    setAnalyzing(true);
    setAnalysisError("");
    setAnalysisResult(null);

    try {
      const resp = await api.executeTool("meta_mcp", "harness_analyze", {
        source_path: sourcePath.trim(),
        source_type: "local",
        software_name: softwareName.trim() || "",
        full: fullExtraction,
      });
      if (isSuccessResponse(resp)) {
        const d = resp.data as { spec: ToolSurfaceSpec; warnings: string[] } | undefined;
        if (d?.spec) {
          setAnalysisResult({ spec: d.spec, warnings: d.warnings || [] });
          setStep("results");
        } else {
          setAnalysisError("Unexpected response format from analyzer.");
        }
      } else {
        setAnalysisError(getErrorMessage(resp));
      }
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  }, [sourcePath, softwareName, fullExtraction]);

  const doGenerate = useCallback(async () => {
    if (!analysisResult || !targetPath.trim()) return;
    setGenerating(true);
    setGenerateError("");
    setGenerateResult(null);

    try {
      const resp = await api.executeTool("meta_mcp", "harness_generate", {
        spec_dict: analysisResult.spec as unknown as Record<string, unknown>,
        target_path: targetPath.trim(),
        author: authorName.trim() || "Harness Generator",
        include_nsis: includeNsis,
      });
      if (isSuccessResponse(resp)) {
        const d = resp.data as
          | {
              generated_path: string;
              file_count: number;
              tool_groups: number;
              operations: number;
              backend_engine: string;
            }
          | undefined;
        if (d) {
          setGenerateResult(d);
          setStep("done");
        } else {
          setGenerateError("Unexpected response format.");
        }
      } else {
        setGenerateError(getErrorMessage(resp));
      }
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }, [analysisResult, targetPath, authorName, includeNsis]);

  const doRefine = useCallback(async () => {
    if (!analysisResult || !targetPath.trim()) return;
    setRefining(true);
    setRefineReport(null);

    try {
      const resp = await api.executeTool("meta_mcp", "harness_refine", {
        operation: "gap",
        server_path: targetPath.trim(),
        source_path: sourcePath.trim(),
        software_name: softwareName.trim() || "",
      });
      if (isSuccessResponse(resp)) {
        const d = resp.data as
          | {
              report: {
                missing_groups: string[];
                total_missing: number;
                total_existing: number;
                unchanged_groups: string[];
              };
            }
          | undefined;
        if (d?.report) {
          const r = d.report;
          const parts: string[] = [];
          if (r.missing_groups.length > 0) {
            parts.push(
              `${r.missing_groups.length} groups missing (${r.total_missing} operations), `,
            );
          } else {
            parts.push("No missing groups. ");
          }
          parts.push(`${r.total_existing} existing groups`);
          if (r.unchanged_groups.length > 0) {
            parts.push(`, ${r.unchanged_groups.length} up to date`);
          }
          setRefineReport(parts.join(""));
        }
      } else {
        setRefineReport(`Refine check error: ${getErrorMessage(resp)}`);
      }
    } catch (err) {
      setRefineReport(err instanceof Error ? err.message : "Refine check failed");
    } finally {
      setRefining(false);
    }
  }, [analysisResult, targetPath, sourcePath, softwareName]);

  // Keyboard shortcut: Enter to analyze
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter" && step === "source" && sourcePath.trim() && !analyzing) {
        doAnalyze();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [step, sourcePath, analyzing, doAnalyze]);

  const spec = analysisResult?.spec;

  return (
    <div className="h-full flex flex-col overflow-y-auto">
      <div className="flex-1 p-8 max-w-5xl mx-auto w-full">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-500/10 rounded-xl">
              <Terminal size={22} className="text-blue-400" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100">Harness Generator</h1>
          </div>
          <p className="text-base text-slate-400 max-w-2xl ml-12">
            Generate a FastMCP server from existing Python source code. The analyzer extracts
            function signatures, groups them by domain, and creates portmanteau tools with
            SOTA-compliant docstrings.
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-3 mb-8 text-sm flex-wrap">
          <StepBadge label="1. Source" active={step === "source"} done={step !== "source"} />
          <div className="w-8 h-px bg-slate-700" />
          <StepBadge
            label="2. Preview"
            active={step === "results"}
            done={step === "generate" || step === "done"}
          />
          <div className="w-8 h-px bg-slate-700" />
          <StepBadge label="3. Generate" active={step === "generate"} done={step === "done"} />
        </div>

        {/* Step 1: Source */}
        {step === "source" && (
          <div className="space-y-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-5">
              <div className="flex items-center gap-3">
                <Search size={18} className="text-blue-400" />
                <h2 className="text-lg font-semibold text-slate-200">Source Code</h2>
              </div>

              <div className="space-y-2">
                <label htmlFor="source-path" className="text-sm font-medium text-slate-300">
                  Source path
                </label>
                <input
                  id="source-path"
                  type="text"
                  value={sourcePath}
                  onChange={(e) => setSourcePath(e.target.value)}
                  placeholder="D:/projects/my-tool or https://github.com/owner/repo"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-5 py-4 text-base text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors placeholder:text-slate-600"
                />
                <p className="text-sm text-slate-500">
                  Path to a directory of Python source files. GitHub URL support coming soon.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label htmlFor="sw-name" className="text-sm font-medium text-slate-300">
                    Software name (optional)
                  </label>
                  <input
                    id="sw-name"
                    type="text"
                    value={softwareName}
                    onChange={(e) => setSoftwareName(e.target.value)}
                    placeholder="Auto-detected from path"
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3.5 text-base text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors placeholder:text-slate-600"
                  />
                </div>
              </div>

              <label className="flex items-start gap-3 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={fullExtraction}
                  onChange={(e) => setFullExtraction(e.target.checked)}
                  className="mt-0.5 rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                />
                <div>
                  <div className="text-sm font-medium text-slate-300 group-hover:text-slate-200">
                    Full extraction
                  </div>
                  <div className="text-sm text-slate-500">
                    Skip curation — exposes every public function found, including undocumented
                    ones. Default: only exports documented functions with type hints.
                  </div>
                </div>
              </label>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={doAnalyze}
                disabled={!sourcePath.trim() || analyzing}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-xl font-medium transition-all flex items-center gap-2 text-base"
              >
                {analyzing ? (
                  <>
                    <Loader2 size={20} className="animate-spin" /> Analyzing...
                  </>
                ) : (
                  <>
                    <Zap size={20} /> Analyze Source
                  </>
                )}
              </button>
            </div>

            {analysisError && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-center gap-2">
                <AlertTriangle size={18} />
                {analysisError}
              </div>
            )}
          </div>
        )}

        {/* Step 2: Results / Preview */}
        {step === "results" && spec && (
          <div className="space-y-6">
            {/* Summary stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <div className="text-sm text-slate-400">Operations</div>
                <div className="text-2xl font-bold text-slate-200 mt-1">
                  {spec.total_operations_curated}
                </div>
                <div className="text-xs text-slate-500">of {spec.total_operations_found} found</div>
              </div>
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <div className="text-sm text-slate-400">Tool groups</div>
                <div className="text-2xl font-bold text-slate-200 mt-1">
                  {spec.tool_groups.length}
                </div>
              </div>
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <div className="text-sm text-slate-400">Backend</div>
                <div className="text-lg font-bold text-slate-200 mt-1 truncate">
                  {spec.backend_engine}
                </div>
              </div>
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <div className="text-sm text-slate-400">State model</div>
                <div className="text-lg font-bold text-slate-200 mt-1">{spec.state_model}</div>
              </div>
            </div>

            {/* Tool groups */}
            <div>
              <h2 className="text-lg font-semibold text-slate-200 mb-4">
                Tool groups ({spec.tool_groups.length})
              </h2>
              <div className="space-y-3">
                {spec.tool_groups.map((g) => (
                  <DrilledGroup key={g.name} group={g} />
                ))}
              </div>
            </div>

            {/* Warnings */}
            {analysisResult.warnings.length > 0 && (
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl space-y-2">
                <div className="text-sm font-medium text-amber-400 flex items-center gap-2">
                  <AlertTriangle size={16} />
                  Warnings
                </div>
                {analysisResult.warnings.map((w) => (
                  <div key={w.slice(0, 40)} className="text-sm text-amber-300/80">
                    {w}
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setStep("generate")}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium transition-all flex items-center gap-2 text-base"
              >
                <Server size={20} /> Continue to Generate
              </button>
              <button
                type="button"
                onClick={() => setStep("source")}
                className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium transition-all text-base"
              >
                Back to Source
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Generate */}
        {step === "generate" && (
          <div className="space-y-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-5">
              <div className="flex items-center gap-3">
                <Settings2 size={18} className="text-blue-400" />
                <h2 className="text-lg font-semibold text-slate-200">Generation options</h2>
              </div>

              <div className="space-y-2">
                <label htmlFor="output-dir" className="text-sm font-medium text-slate-300">
                  Output directory
                </label>
                <input
                  id="output-dir"
                  type="text"
                  value={targetPath}
                  onChange={(e) => setTargetPath(e.target.value)}
                  placeholder="D:/repos/generated-server"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-5 py-4 text-base text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors placeholder:text-slate-600"
                />
                <p className="text-sm text-slate-500">
                  A new folder will be created here with the full server.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label htmlFor="author-name" className="text-sm font-medium text-slate-300">
                    Author
                  </label>
                  <input
                    id="author-name"
                    type="text"
                    value={authorName}
                    onChange={(e) => setAuthorName(e.target.value)}
                    placeholder="Your name"
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3.5 text-base text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors placeholder:text-slate-600"
                  />
                </div>
              </div>

              <label className="flex items-start gap-3 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={includeNsis}
                  onChange={(e) => setIncludeNsis(e.target.checked)}
                  className="mt-0.5 rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                />
                <div>
                  <div className="text-sm font-medium text-slate-300 group-hover:text-slate-200">
                    Include Tauri + NSIS wrapper
                  </div>
                  <div className="text-sm text-slate-500">
                    Adds native/ directory with Cargo.toml, build.ps1, and PyInstaller spec for
                    shipping as a single-installer desktop app.
                  </div>
                </div>
              </label>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={doGenerate}
                disabled={!targetPath.trim() || generating}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-xl font-medium transition-all flex items-center gap-2 text-base"
              >
                {generating ? (
                  <>
                    <Loader2 size={20} className="animate-spin" /> Generating...
                  </>
                ) : (
                  <>
                    <Code2 size={20} /> Generate Server
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={() => setStep("results")}
                className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium transition-all text-base"
              >
                Back to Preview
              </button>
            </div>

            {generateError && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-center gap-2">
                <AlertTriangle size={18} />
                {generateError}
              </div>
            )}
          </div>
        )}

        {/* Step 4: Done */}
        {step === "done" && generateResult && (
          <div className="space-y-6">
            <div className="bg-green-500/10 border border-green-500/20 rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-3">
                <CheckCircle size={24} className="text-green-400" />
                <h2 className="text-xl font-bold text-slate-200">Server generated</h2>
              </div>
              <p className="text-slate-400 mb-4 max-w-xl">
                The server was created successfully. The portmanteau tools are ready to use.
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-black/30 rounded-lg p-3">
                  <div className="text-sm text-slate-400">Files created</div>
                  <div className="text-xl font-bold text-slate-200">
                    {generateResult.file_count}
                  </div>
                </div>
                <div className="bg-black/30 rounded-lg p-3">
                  <div className="text-sm text-slate-400">Tool groups</div>
                  <div className="text-xl font-bold text-slate-200">
                    {generateResult.tool_groups}
                  </div>
                </div>
                <div className="bg-black/30 rounded-lg p-3">
                  <div className="text-sm text-slate-400">Operations</div>
                  <div className="text-xl font-bold text-slate-200">
                    {generateResult.operations}
                  </div>
                </div>
                <div className="bg-black/30 rounded-lg p-3">
                  <div className="text-sm text-slate-400">Backend</div>
                  <div className="text-lg font-bold text-slate-200 truncate">
                    {generateResult.backend_engine}
                  </div>
                </div>
              </div>

              <div className="mt-4 bg-black/30 rounded-lg px-4 py-3 flex items-center gap-2 text-sm">
                <FileCode2 size={16} className="text-slate-500" />
                <span className="text-slate-400 font-mono">{generateResult.generated_path}</span>
              </div>
            </div>

            {/* Refine check */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-slate-200">Refinement check</h3>
                  <p className="text-sm text-slate-400">
                    Compare the generated server against the original source for gaps.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={doRefine}
                  disabled={refining || !targetPath.trim()}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 rounded-lg font-medium transition-all flex items-center gap-2 text-sm"
                >
                  {refining ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <RefreshCw size={16} />
                  )}
                  Check for gaps
                </button>
              </div>

              {refineReport && (
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-sm text-slate-400">
                  {refineReport}
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setStep("source");
                  setAnalysisResult(null);
                  setGenerateResult(null);
                  setRefineReport(null);
                }}
                className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium transition-all flex items-center gap-2 text-base"
              >
                <RefreshCw size={20} /> New Analysis
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
