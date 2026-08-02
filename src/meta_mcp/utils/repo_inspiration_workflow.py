"""Path picking and sampling helpers for inspire_repo_workflow (Phase C)."""

from __future__ import annotations

from meta_mcp.utils.github_inspiration import smart_pick_files


def pick_paths_deterministic(
    paths: list[str],
    *,
    max_paths: int = 5,
    language_hint: str | None = None,
    suggested_subpaths: list[str] | None = None,
) -> list[str]:
    """Choose study paths without LLM sampling."""
    if suggested_subpaths:
        prefix = suggested_subpaths[0]
        scoped = [p for p in paths if p == prefix or p.startswith(f"{prefix}/")]
        if scoped:
            return smart_pick_files(scoped, max_paths, language_hint=language_hint)
    return smart_pick_files(paths, max_paths, language_hint=language_hint)


def parse_paths_from_sampling(text: str, valid_paths: set[str]) -> list[str]:
    """Extract file paths mentioned in an LLM reply that exist in the repo tree."""
    if not text or not valid_paths:
        return []
    found: list[str] = []
    for line in text.splitlines():
        line = line.strip().strip("-*`").strip()
        if not line or (" " in line and not line.endswith((".py", ".ts", ".tsx", ".js", ".go", ".rs"))):
            # try last token as path
            parts = line.split()
            if parts:
                line = parts[-1]
        if line in valid_paths:
            found.append(line)
            continue
        for path in valid_paths:
            if path.endswith(line) or path == line:
                found.append(path)
                break
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for p in found:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def extract_sampling_text(reply: object) -> str:
    if reply is None:
        return ""
    text = getattr(reply, "text", None)
    if text:
        return str(text)
    content = getattr(reply, "content", None)
    if content:
        return str(content)
    return str(reply)


WORKFLOW_SYNTHESIS_SYSTEM = (
    "You summarize open-source repository architecture for a developer studying patterns. "
    "Be concise. Explain organization, stack, and design ideas  do not paste large code blocks."
)
