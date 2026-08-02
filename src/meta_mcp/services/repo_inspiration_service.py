"""Remote GitHub repository inspiration (native Python).

Workflow adapted from Repomuse (https://www.npmjs.com/package/repomuse, MIT, praveene3127).
"""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from typing import Any

import aiohttp

from meta_mcp.services.base import MetaMCPService
from meta_mcp.utils.github_inspiration import (
    MANIFEST_NAMES,
    RepoRef,
    api_error_message,
    filter_blob_paths,
    github_auth_token,
    match_target_files,
    parse_github_url,
    smart_pick_files,
    truncate_content,
)
from meta_mcp.utils.repo_inspiration_cache import CachedTreeEntry, get_file_cache, get_tree_cache
from meta_mcp.utils.repo_inspiration_hints import (
    build_directory_summary_text,
    build_study_hints,
    infer_language_hint_from_tree,
    is_large_repo_context,
    suggest_subpaths,
)
from meta_mcp.utils.repo_inspiration_profiles import (
    INSPIRE_REPO_HELP,
    ProfileLimits,
    apply_subpath_filter,
    compose_files_chapters,
    compose_patterns_chapters,
    compose_structure_chapters,
    filter_path_globs,
    get_profile_limits,
    gitingest_url,
    make_chapter,
    normalize_profile,
)
from meta_mcp.utils.repo_inspiration_workflow import (
    WORKFLOW_SYNTHESIS_SYSTEM,
    extract_sampling_text,
    parse_paths_from_sampling,
    pick_paths_deterministic,
)


@dataclass
class InspirationContext:
    ref: RepoRef
    branch: str
    tree: list[dict[str, Any]]
    truncated: bool
    paths: list[str]
    profile: str
    limits: ProfileLimits
    subpath: str | None
    tree_cached: bool
    repo_meta: dict[str, Any] | None = None


class GitHubInspirationClient:
    """Minimal GitHub REST + raw client for public (or token-authenticated) repos."""

    def __init__(self, token: str | None = None) -> None:
        self._token = token if token is not None else github_auth_token()
        self.last_rate_limit_remaining: int | None = None
        self.raw_fetch_count: int = 0

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "MetaMCP-RepoInspiration/1.2",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get_default_branch(self, session: aiohttp.ClientSession, owner: str, repo: str) -> str:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        async with session.get(url, headers=self._headers()) as resp:
            if resp.status != 200:
                raise ValueError(api_error_message(resp.status, f"Fetching repo info for {owner}/{repo}"))
            data = await resp.json()
            return data.get("default_branch") or "main"

    async def get_repo_meta(self, session: aiohttp.ClientSession, owner: str, repo: str) -> dict[str, Any]:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        async with session.get(url, headers=self._headers()) as resp:
            if resp.status != 200:
                raise ValueError(api_error_message(resp.status, f"Fetching repo metadata for {owner}/{repo}"))
            data = await resp.json()
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining is not None:
                with contextlib.suppress(ValueError, TypeError):
                    self.last_rate_limit_remaining = int(remaining)
            return {
                "description": data.get("description") or "",
                "topics": data.get("topics") or [],
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "license": (data.get("license") or {}).get("spdx_id") or "",
                "language": data.get("language") or "",
                "archived": bool(data.get("archived")),
                "updated_at": data.get("pushed_at") or "",
                "created_at": data.get("created_at") or "",
                "default_branch": data.get("default_branch") or "main",
                "open_issues": data.get("open_issues_count", 0),
                "homepage": data.get("homepage") or "",
            }

    async def get_tree(
        self, session: aiohttp.ClientSession, owner: str, repo: str, branch: str
    ) -> tuple[list[dict[str, Any]], bool]:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        async with session.get(url, headers=self._headers()) as resp:
            if resp.status != 200:
                raise ValueError(api_error_message(resp.status, f"Fetching file tree for {owner}/{repo}"))
            data = await resp.json()
            truncated = bool(data.get("truncated"))
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining is not None:
                with contextlib.suppress(ValueError, TypeError):
                    self.last_rate_limit_remaining = int(remaining)
            return list(data.get("tree") or []), truncated

    async def get_file_content(
        self, session: aiohttp.ClientSession, owner: str, repo: str, path: str, branch: str
    ) -> str:
        file_cache = get_file_cache()
        cached = file_cache.get(owner, repo, branch, path)
        if cached is not None:
            return cached
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        headers: dict[str, str] = {"User-Agent": "MetaMCP-RepoInspiration/1.2"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self.raw_fetch_count += 1
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise ValueError(f'Could not fetch "{path}" (HTTP {resp.status})')
            content = await resp.text()
            file_cache.set(owner, repo, branch, path, content)
            return content


class RepoInspirationService(MetaMCPService):
    """Fetch and summarize public GitHub repos for agent inspiration context."""

    def __init__(self, client: GitHubInspirationClient | None = None) -> None:
        super().__init__()
        self._client = client or GitHubInspirationClient()
        self._cache = get_tree_cache()

    @staticmethod
    def _classify_error(error_message: str) -> str:
        msg_lower = error_message.lower()
        if "access denied" in msg_lower or "401" in msg_lower or "403" in msg_lower:
            return "auth"
        if "not found" in msg_lower or "404" in msg_lower:
            return "not_found"
        if "rate limit" in msg_lower or "429" in msg_lower:
            return "rate_limited"
        if "network error" in msg_lower:
            return "network"
        if "invalid" in msg_lower or "unknown" in msg_lower:
            return "invalid_input"
        return "unknown"

    def _apply_max_chars(self, limits: ProfileLimits, max_chars: int | None) -> ProfileLimits:
        if max_chars is None or max_chars <= 0:
            return limits
        cap = min(max_chars, limits.total_chars)
        if cap == limits.total_chars:
            return limits
        return ProfileLimits(
            structure_max_shown=limits.structure_max_shown,
            auto_files=limits.auto_files,
            explicit_files=limits.explicit_files,
            total_chars=cap,
            per_file_chars=min(limits.per_file_chars, cap // 4),
            pattern_structure_lines=limits.pattern_structure_lines,
            pattern_source_files=limits.pattern_source_files,
            pattern_source_budget=min(limits.pattern_source_budget, cap // 2),
            readme_limit=min(limits.readme_limit, cap // 8),
            manifest_limit=min(limits.manifest_limit, cap // 10),
        )

    async def _load_context(
        self,
        url: str,
        *,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "standard",
        max_chars: int | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
        extra_ignores: list[str] | None = None,
    ) -> InspirationContext:
        ref = parse_github_url(url)
        if not ref:
            raise ValueError(f'Invalid GitHub URL: "{url}". Expected https://github.com/owner/repo')
        prof = normalize_profile(profile)
        limits = self._apply_max_chars(get_profile_limits(prof), max_chars)
        resolved_branch = (branch or ref.branch or "").strip() or None
        tree_cached = False

        timeout = aiohttp.ClientTimeout(total=120)
        repo_meta: dict[str, Any] | None = None
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if not resolved_branch:
                resolved_branch = await self._client.get_default_branch(session, ref.owner, ref.repo)
            try:
                repo_meta = await self._client.get_repo_meta(session, ref.owner, ref.repo)
                if repo_meta:
                    resolved_branch = repo_meta.get("default_branch") or resolved_branch
            except ValueError:
                pass
            cached = self._cache.get(ref.owner, ref.repo, resolved_branch)
            if cached is None:
                tree, truncated = await self._client.get_tree(session, ref.owner, ref.repo, resolved_branch)
                self._cache.set(
                    ref.owner,
                    ref.repo,
                    resolved_branch,
                    CachedTreeEntry(
                        ref=ref,
                        branch=resolved_branch,
                        tree=tree,
                        truncated=truncated,
                        fetched_at=time.time(),
                    ),
                )
            else:
                tree = cached.tree
                truncated = cached.truncated
                tree_cached = True

        paths = filter_blob_paths(tree, extra_ignores)
        paths = apply_subpath_filter(paths, subpath)
        paths = filter_path_globs(paths, include_globs, exclude_globs)
        return InspirationContext(
            ref=ref,
            branch=resolved_branch,
            tree=tree,
            truncated=truncated,
            paths=paths,
            profile=prof,
            limits=limits,
            subpath=subpath,
            tree_cached=tree_cached,
            repo_meta=repo_meta,
        )

    def _base_meta(self, ctx: InspirationContext) -> dict[str, Any]:
        meta = {
            "owner": ctx.ref.owner,
            "repo": ctx.ref.repo,
            "branch": ctx.branch,
            "profile": ctx.profile,
            "subpath": ctx.subpath,
            "gitingest_url": gitingest_url(ctx.ref.owner, ctx.ref.repo, ctx.branch, ctx.subpath),
            "tree_cached": ctx.tree_cached,
            "tree_truncated_by_github": ctx.truncated,
        }
        remaining = getattr(self._client, "last_rate_limit_remaining", None)
        if remaining is not None:
            meta["rate_limit_remaining"] = remaining
        raw_fetches = getattr(self._client, "raw_fetch_count", 0)
        meta["raw_fetches"] = raw_fetches
        if ctx.repo_meta:
            meta["repo_meta"] = ctx.repo_meta
        return meta

    def _study_enrichment(self, ctx: InspirationContext) -> dict[str, Any]:
        large = is_large_repo_context(truncated_github=ctx.truncated, path_count=len(ctx.paths))
        suggested_subpaths = suggest_subpaths(ctx.paths) if large and not ctx.subpath else []
        suggested_language = infer_language_hint_from_tree(ctx.tree)
        hints = build_study_hints(
            owner=ctx.ref.owner,
            repo=ctx.ref.repo,
            branch=ctx.branch,
            truncated_github=ctx.truncated,
            path_count=len(ctx.paths),
            subpath=ctx.subpath,
            gitingest_url=gitingest_url(ctx.ref.owner, ctx.ref.repo, ctx.branch, ctx.subpath),
            suggested_subpaths=suggested_subpaths,
            suggested_language_hint=suggested_language,
        )
        out: dict[str, Any] = {
            "large_repo_mode": large,
            "hints": hints,
            "suggested_subpaths": suggested_subpaths,
            "suggested_language_hint": suggested_language,
        }
        if large:
            out["directory_summary"] = build_directory_summary_text(ctx.paths)
        return out

    def _resolve_language_hint(self, ctx: InspirationContext, language_hint: str | None) -> str | None:
        if language_hint and language_hint.strip():
            return language_hint.strip()
        return infer_language_hint_from_tree(ctx.tree)

    async def inspire_structure(
        self,
        url: str,
        *,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "standard",
        max_chars: int | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            ctx = await self._load_context(
                url,
                subpath=subpath,
                branch=branch,
                profile=profile,
                max_chars=max_chars,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
            )
            total = len(ctx.paths)
            enrich = self._study_enrichment(ctx)
            large = bool(enrich.get("large_repo_mode"))
            chapters, text = compose_structure_chapters(
                ctx.ref.owner,
                ctx.ref.repo,
                ctx.branch,
                ctx.paths,
                total,
                ctx.limits,
                subpath=ctx.subpath,
                truncated_github=ctx.truncated,
                large_repo_mode=large,
                directory_summary=enrich.get("directory_summary"),
                study_hints=enrich.get("hints"),
                repo_meta=ctx.repo_meta,
            )
            data = {
                **self._base_meta(ctx),
                **enrich,
                "text": text,
                "chapters": chapters,
                "total_source_files": total,
                "shown_files": min(total, ctx.limits.structure_max_shown),
                "char_count": len(text),
            }
            return self.create_response(
                True,
                f"Structure for {ctx.ref.owner}/{ctx.ref.repo}@{ctx.branch}",
                data,
            )
        except ValueError as e:
            return self.create_response(False, str(e), error_type=self._classify_error(str(e)))
        except aiohttp.ClientError as e:
            return self.create_response(False, f"Network error: {e!s}", error_type="network")

    async def inspire_files(
        self,
        url: str,
        target_files: list[str] | None = None,
        *,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "standard",
        max_chars: int | None = None,
        language_hint: str | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            ctx = await self._load_context(
                url,
                subpath=subpath,
                branch=branch,
                profile=profile,
                max_chars=max_chars,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
            )
            all_paths = ctx.paths
            explicit = [t for t in (target_files or []) if (t or "").strip()]
            if explicit:
                file_paths = match_target_files(all_paths, explicit)[: ctx.limits.explicit_files]
                if not file_paths:
                    text = "\n".join(
                        [
                            f"warning:   None of the requested files were found in {ctx.ref.owner}/{ctx.ref.repo}.",
                            f"Requested: {', '.join(explicit)}",
                            "",
                            "tip:  Call inspire_repo(operation=structure) first to list available paths.",
                        ]
                    )
                    return self.create_response(
                        False,
                        "No matching files",
                        {
                            **self._base_meta(ctx),
                            "text": text,
                            "chapters": [
                                {
                                    "id": "hint-missing",
                                    "title": "No matching files",
                                    "kind": "hint",
                                    "body": text,
                                }
                            ],
                        },
                        error_type="not_found",
                    )
            else:
                resolved_lang = self._resolve_language_hint(ctx, language_hint)
                file_paths = smart_pick_files(all_paths, ctx.limits.auto_files, language_hint=resolved_lang)

            timeout = aiohttp.ClientTimeout(total=120)
            contents: list[tuple[str, str | None, str | None]] = []
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for path in file_paths:
                    try:
                        content = await self._client.get_file_content(
                            session, ctx.ref.owner, ctx.ref.repo, path, ctx.branch
                        )
                        contents.append((path, content, None))
                    except ValueError as err:
                        contents.append((path, None, str(err)))

            chapters, text = compose_files_chapters(
                ctx.ref.owner, ctx.ref.repo, ctx.branch, file_paths, contents, ctx.limits
            )
            enrich = self._study_enrichment(ctx)
            if enrich.get("hints"):
                chapters.append(
                    make_chapter(
                        "hints",
                        "Study hints",
                        "hint",
                        "\n".join(f" {h}" for h in enrich["hints"]),
                    )
                )
            if len(text) > ctx.limits.total_chars:
                text = text[: ctx.limits.total_chars] + "\n\nwarning:   Output capped by profile/max_chars."
            resolved_lang = self._resolve_language_hint(ctx, language_hint)
            return self.create_response(
                True,
                f"Fetched {len(file_paths)} file(s) from {ctx.ref.owner}/{ctx.ref.repo}",
                {
                    **self._base_meta(ctx),
                    **enrich,
                    "text": text,
                    "chapters": chapters,
                    "files": file_paths,
                    "char_count": len(text),
                    "auto_selected": not explicit,
                    "language_hint": resolved_lang,
                },
            )
        except ValueError as e:
            return self.create_response(False, str(e), error_type=self._classify_error(str(e)))
        except aiohttp.ClientError as e:
            return self.create_response(False, f"Network error: {e!s}", error_type="network")

    async def inspire_patterns(
        self,
        url: str,
        *,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "standard",
        max_chars: int | None = None,
        language_hint: str | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            ctx = await self._load_context(
                url,
                subpath=subpath,
                branch=branch,
                profile=profile,
                max_chars=max_chars,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
            )
            all_paths = ctx.paths
            readme = ""
            manifest_paths: list[tuple[str, str]] = []
            source_blocks: list[tuple[str, str]] = []

            readme_item = next(
                (i for i in ctx.tree if (i.get("path") or "").lower() == "readme.md"),
                None,
            )
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if readme_item and readme_item.get("path"):
                    try:
                        raw = await self._client.get_file_content(
                            session,
                            ctx.ref.owner,
                            ctx.ref.repo,
                            readme_item["path"],
                            ctx.branch,
                        )
                        readme = truncate_content(raw, ctx.limits.readme_limit)
                    except ValueError:
                        pass

                for manifest in MANIFEST_NAMES:
                    match = next(
                        (i for i in ctx.tree if (i.get("path") or "").lower() == manifest),
                        None,
                    )
                    if not match or not match.get("path"):
                        continue
                    try:
                        raw = await self._client.get_file_content(
                            session,
                            ctx.ref.owner,
                            ctx.ref.repo,
                            match["path"],
                            ctx.branch,
                        )
                        manifest_paths.append((match["path"], truncate_content(raw, ctx.limits.manifest_limit)))
                    except ValueError:
                        pass

                resolved_lang = self._resolve_language_hint(ctx, language_hint)
                source_chars = 0
                for path in smart_pick_files(
                    all_paths,
                    ctx.limits.pattern_source_files,
                    language_hint=resolved_lang,
                ):
                    try:
                        raw = await self._client.get_file_content(
                            session, ctx.ref.owner, ctx.ref.repo, path, ctx.branch
                        )
                        body = truncate_content(raw, ctx.limits.per_file_chars)
                        source_blocks.append((path, body))
                        source_chars += len(body)
                        if source_chars > ctx.limits.pattern_source_budget:
                            break
                    except ValueError:
                        continue

            chapters, text = compose_patterns_chapters(
                ctx.ref.owner,
                ctx.ref.repo,
                ctx.branch,
                all_paths,
                readme,
                manifest_paths,
                source_blocks,
                ctx.limits,
                subpath=ctx.subpath,
                profile=ctx.profile,
            )
            enrich = self._study_enrichment(ctx)
            if enrich.get("hints"):
                chapters.append(
                    make_chapter(
                        "hints",
                        "Study hints",
                        "hint",
                        "\n".join(f" {h}" for h in enrich["hints"]),
                    )
                )
            if len(text) > ctx.limits.total_chars:
                text = text[: ctx.limits.total_chars] + "\n\nwarning:   Output capped by profile/max_chars."

            resolved_lang = self._resolve_language_hint(ctx, language_hint)
            return self.create_response(
                True,
                f"Pattern analysis pack for {ctx.ref.owner}/{ctx.ref.repo}",
                {
                    **self._base_meta(ctx),
                    **enrich,
                    "text": text,
                    "chapters": chapters,
                    "total_source_files": len(all_paths),
                    "char_count": len(text),
                    "language_hint": resolved_lang,
                },
            )
        except ValueError as e:
            return self.create_response(False, str(e), error_type=self._classify_error(str(e)))
        except aiohttp.ClientError as e:
            return self.create_response(False, f"Network error: {e!s}", error_type="network")

    async def inspire_repo(
        self,
        operation: str,
        url: str,
        target_files: list[str] | None = None,
        *,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "standard",
        max_chars: int | None = None,
        language_hint: str | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
    ) -> dict[str, Any]:
        op = (operation or "").strip().lower()
        if op in ("help", "?"):
            return self.create_response(
                True,
                "inspire_repo help",
                {
                    "text": INSPIRE_REPO_HELP,
                    "chapters": [
                        {
                            "id": "help",
                            "title": "inspire_repo help",
                            "kind": "prompt",
                            "body": INSPIRE_REPO_HELP,
                        }
                    ],
                    "operation": "help",
                },
            )
        if op == "structure":
            return await self.inspire_structure(
                url,
                subpath=subpath,
                branch=branch,
                profile=profile,
                max_chars=max_chars,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
            )
        if op == "files":
            return await self.inspire_files(
                url,
                target_files,
                subpath=subpath,
                branch=branch,
                profile=profile,
                max_chars=max_chars,
                language_hint=language_hint,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
            )
        if op == "patterns":
            return await self.inspire_patterns(
                url,
                subpath=subpath,
                branch=branch,
                profile=profile,
                max_chars=max_chars,
                language_hint=language_hint,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
            )
        return self.create_response(
            False,
            f'Unknown operation "{operation}". Use structure, files, patterns, or help. '
            "Multi-step: inspire_repo_workflow.",
            error_type="invalid_input",
        )

    async def inspire_repo_workflow(
        self,
        url: str,
        goal: str,
        *,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "brief",
        max_paths: int = 5,
        max_chars: int | None = None,
        language_hint: str | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
        ctx: Any | None = None,
    ) -> dict[str, Any]:
        """Multi-step study: structure  pick paths  files  patterns  optional synthesis."""
        study_goal = (goal or "").strip() or "Understand architecture and patterns"
        cap = max(1, min(max_paths, 15))
        sampling_used = False
        path_pick_sampling = False

        try:
            struct = await self.inspire_structure(
                url,
                subpath=subpath,
                branch=branch,
                profile="brief",
                max_chars=max_chars,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
            )
            if not struct.get("success"):
                return struct

            struct_data = struct.get("data") or {}
            enrich = {k: struct_data.get(k) for k in ("hints", "suggested_subpaths", "suggested_language_hint")}
            load_ctx = await self._load_context(
                url,
                subpath=subpath,
                branch=branch,
                profile=profile,
                max_chars=max_chars,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
            )
            resolved_lang = self._resolve_language_hint(load_ctx, language_hint)
            valid = set(load_ctx.paths)
            picked: list[str] = []

            struct_excerpt = (struct_data.get("text") or "")[:12_000]
            if ctx is not None and hasattr(ctx, "sample") and struct_excerpt:
                try:
                    reply = await ctx.sample(
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Pick up to 5 repository file paths to study for the user's goal. "
                                    "Reply with one path per line. Only paths that appear in the listing."
                                ),
                            },
                            {
                                "role": "user",
                                "content": f"Goal: {study_goal}\n\nRepository listing:\n{struct_excerpt}",
                            },
                        ],
                    )
                    picked = parse_paths_from_sampling(extract_sampling_text(reply), valid)[:cap]
                    if picked:
                        path_pick_sampling = True
                        sampling_used = True
                except Exception as exc:
                    self.logger.warning("Workflow path sampling failed", error=str(exc))

            if not picked:
                picked = pick_paths_deterministic(
                    load_ctx.paths,
                    max_paths=cap,
                    language_hint=resolved_lang,
                    suggested_subpaths=enrich.get("suggested_subpaths"),
                )

            files = await self.inspire_files(
                url,
                picked,
                subpath=subpath,
                branch=branch,
                profile=profile or "brief",
                max_chars=max_chars,
                language_hint=resolved_lang,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
            )
            patterns = await self.inspire_patterns(
                url,
                subpath=subpath,
                branch=branch,
                profile=profile or "brief",
                max_chars=max_chars,
                language_hint=resolved_lang,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
            )

            synthesis = (
                f"## Workflow: {study_goal}\n\n"
                f"Steps: structure  {len(picked)} file(s)  patterns.\n"
                f"Path selection: {'sampling' if path_pick_sampling else 'deterministic'}.\n\n"
                "Review the patterns chapter for architecture notes; file chapters contain source context."
            )
            patterns_text = ""
            if patterns.get("success"):
                patterns_text = (patterns.get("data") or {}).get("text") or ""
            if ctx is not None and hasattr(ctx, "sample") and patterns_text:
                try:
                    reply = await ctx.sample(
                        messages=[
                            {"role": "system", "content": WORKFLOW_SYNTHESIS_SYSTEM},
                            {
                                "role": "user",
                                "content": (f"Goal: {study_goal}\n\nPattern pack excerpt:\n{patterns_text[:20_000]}"),
                            },
                        ],
                    )
                    sampled = extract_sampling_text(reply).strip()
                    if sampled:
                        synthesis = sampled
                        sampling_used = True
                except Exception as exc:
                    self.logger.warning("Workflow synthesis sampling failed", error=str(exc))

            chapters: list[dict[str, Any]] = []
            for block in (struct, files, patterns):
                if block.get("success"):
                    chapters.extend((block.get("data") or {}).get("chapters") or [])
            chapters.append(
                make_chapter("workflow-synthesis", "Workflow synthesis", "prompt", synthesis),
            )

            combined_text = "\n\n".join(
                part
                for part in [
                    synthesis,
                    (files.get("data") or {}).get("text", "")[:4000] if files.get("success") else "",
                ]
                if part
            )

            return self.create_response(
                True,
                f"Workflow complete for {load_ctx.ref.owner}/{load_ctx.ref.repo}",
                {
                    **self._base_meta(load_ctx),
                    **self._study_enrichment(load_ctx),
                    "goal": study_goal,
                    "workflow_steps": ["structure", "files", "patterns", "synthesis"],
                    "selected_files": picked,
                    "sampling_used": sampling_used,
                    "path_pick_sampling": path_pick_sampling,
                    "structure": struct_data,
                    "files": files.get("data"),
                    "patterns": patterns.get("data"),
                    "text": combined_text,
                    "chapters": chapters,
                    "char_count": len(combined_text),
                },
            )
        except ValueError as e:
            return self.create_response(False, str(e), error_type=self._classify_error(str(e)))
        except aiohttp.ClientError as e:
            return self.create_response(False, f"Network error: {e!s}", error_type="network")
