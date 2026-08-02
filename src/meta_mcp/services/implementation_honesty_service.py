from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from meta_mcp.services.base import MetaMCPService


class ImplementationHonestyService(MetaMCPService):
    """Scan repositories for stub/mock/gaslight runtime patterns."""

    DEFAULT_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx"}
    DEFAULT_IGNORE_PARTS = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        ".pytest_cache",
        ".ruff_cache",
    }
    DEFAULT_ALLOW_PARTS = {"tests", "test", "docs", "examples", "example", "fixtures"}

    BANNED_PATTERNS = [
        re.compile(r"\bsimulat(e|ed|ion)\b", re.IGNORECASE),
        re.compile(r"\bmock response\b", re.IGNORECASE),
        re.compile(r"\bplaceholder implementation\b", re.IGNORECASE),
        re.compile(r"\breturn (a |the )?placeholder\b", re.IGNORECASE),
        re.compile(r"\bstatic list for demonstration\b", re.IGNORECASE),
        re.compile(r"\bfor now, we('| wi)ll\b", re.IGNORECASE),
        re.compile(r"\bsample security finding\b", re.IGNORECASE),
        re.compile(r"\bdummy class(?:es)?\b", re.IGNORECASE),
    ]

    ALLOW_TEXT_PATTERNS = [
        re.compile(r"under construction", re.IGNORECASE),
        re.compile(r"not_implemented", re.IGNORECASE),
        re.compile(r"prototype_only", re.IGNORECASE),
    ]

    async def scan(
        self,
        target_path: str,
        mode: str = "audit",
        include_extensions: list[str] | None = None,
        max_findings: int = 500,
        baseline_path: str | None = None,
    ) -> dict[str, Any]:
        """Scan runtime code for implementation honesty violations."""
        path = Path(target_path).expanduser().resolve()
        if not path.exists():
            return self.create_response(False, f"Target path does not exist: {target_path}")
        if mode not in {"audit", "enforce", "baseline_create", "baseline_enforce"}:
            return self.create_response(
                False,
                f"Unsupported mode '{mode}'. Use 'audit', 'enforce', 'baseline_create', or 'baseline_enforce'.",
            )

        extensions = set(include_extensions or self.DEFAULT_EXTENSIONS)
        findings: list[dict[str, Any]] = []
        scanned_files = 0

        for file_path in path.rglob("*"):
            if not file_path.is_file() or file_path.suffix.lower() not in extensions:
                continue
            if self._should_skip(file_path):
                continue

            scanned_files += 1
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if any(allow.search(line) for allow in self.ALLOW_TEXT_PATTERNS):
                    continue
                for pattern in self.BANNED_PATTERNS:
                    if pattern.search(line):
                        findings.append(
                            {
                                "file": str(file_path),
                                "line": line_no,
                                "pattern": pattern.pattern,
                                "text": line.strip(),
                            }
                        )
                        break
                if len(findings) >= max_findings:
                    break
            if len(findings) >= max_findings:
                break

        violation_count = len(findings)
        passed = violation_count == 0
        should_fail = mode == "enforce" and not passed
        baseline_file = (
            Path(baseline_path).expanduser().resolve()
            if baseline_path
            else path / ".implementation-honesty-baseline.json"
        )

        if mode == "baseline_create":
            baseline_data = {
                "target_path": str(path),
                "violation_count": violation_count,
                "violations": findings,
            }
            baseline_file.write_text(json.dumps(baseline_data, indent=2), encoding="utf-8")
            return self.create_response(
                True,
                f"Baseline created at {baseline_file}",
                data={
                    "mode": mode,
                    "target_path": str(path),
                    "baseline_path": str(baseline_file),
                    "violation_count": violation_count,
                    "violations": findings,
                },
            )

        if mode == "baseline_enforce":
            if not baseline_file.exists():
                return self.create_response(
                    False,
                    f"Baseline file not found: {baseline_file}",
                    data={
                        "mode": mode,
                        "target_path": str(path),
                        "baseline_path": str(baseline_file),
                    },
                )
            try:
                baseline_data = json.loads(baseline_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return self.create_response(
                    False,
                    f"Invalid baseline JSON at {baseline_file}: {exc}",
                    data={
                        "mode": mode,
                        "target_path": str(path),
                        "baseline_path": str(baseline_file),
                    },
                )

            baseline_violations = baseline_data.get("violations", [])
            baseline_keys = {self._violation_key(item) for item in baseline_violations}
            current_keys = {self._violation_key(item) for item in findings}
            new_keys = current_keys - baseline_keys
            new_violations = [item for item in findings if self._violation_key(item) in new_keys]
            should_fail = len(new_violations) > 0
            message = (
                "Baseline enforcement passed. No new implementation honesty violations."
                if not should_fail
                else f"Baseline enforcement failed: {len(new_violations)} new violations detected."
            )
            return self.create_response(
                success=not should_fail,
                message=message,
                data={
                    "mode": mode,
                    "target_path": str(path),
                    "baseline_path": str(baseline_file),
                    "scanned_files": scanned_files,
                    "current_violation_count": violation_count,
                    "baseline_violation_count": len(baseline_violations),
                    "new_violation_count": len(new_violations),
                    "new_violations": new_violations,
                    "all_violations": findings,
                },
            )

        message = (
            "Implementation honesty scan passed."
            if passed
            else f"Found {violation_count} implementation honesty violations."
        )

        return self.create_response(
            success=not should_fail,
            message=message,
            data={
                "mode": mode,
                "target_path": str(path),
                "scanned_files": scanned_files,
                "violations": findings,
                "violation_count": violation_count,
                "next_steps": [
                    "Replace fake-success code paths with explicit not_implemented contracts",
                    "Mark unavailable UI features as Under construction",
                    "Move prototype content to tests/docs/examples where appropriate",
                ],
                "baseline_path": str(baseline_file),
            },
        )

    def _should_skip(self, file_path: Path) -> bool:
        parts = {part.lower() for part in file_path.parts}
        if any(ignore.lower() in parts for ignore in self.DEFAULT_IGNORE_PARTS):
            return True
        return any(allowed.lower() in parts for allowed in self.DEFAULT_ALLOW_PARTS)

    def _violation_key(self, item: dict[str, Any]) -> str:
        return f"{item.get('file', '')}|{item.get('line', '')}|{item.get('pattern', '')}|{item.get('text', '')}"
