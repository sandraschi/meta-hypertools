"""Tests for GitHub repo inspiration utilities and service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meta_mcp.services.repo_inspiration_service import (
    GitHubInspirationClient,
    InspirationContext,
    RepoInspirationService,
)
from meta_mcp.utils.github_inspiration import (
    build_structure_text,
    filter_blob_paths,
    parse_github_url,
    score_file,
    should_ignore,
    smart_pick_files,
)
from meta_mcp.utils.repo_inspiration_cache import get_tree_cache
from meta_mcp.utils.repo_inspiration_hints import (
    build_directory_summary_text,
    infer_language_hint_from_tree,
    is_large_repo_context,
    suggest_subpaths,
)
from meta_mcp.utils.repo_inspiration_profiles import (
    apply_subpath_filter,
    compose_structure_chapters,
    get_profile_limits,
    normalize_profile,
)


def test_parse_github_url_full_and_shorthand():

    ref_fast = parse_github_url("https://github.com/fastapi/fastapi")

    assert ref_fast is not None

    assert ref_fast.owner == "fastapi"

    assert ref_fast.repo == "fastapi"

    assert ref_fast.branch is None

    ref = parse_github_url("github.com/kovidgoyal/calibre")

    assert ref is not None

    assert ref.owner == "kovidgoyal"

    assert ref.repo == "calibre"

    ref2 = parse_github_url("https://github.com/o/r/tree/develop/src")

    assert ref2 is not None

    assert ref2.branch == "develop"

    assert parse_github_url("https://gitlab.com/a/b") is None


def test_should_ignore_lockfiles_and_node_modules():

    assert should_ignore("package-lock.json")

    assert should_ignore("frontend/node_modules/foo/index.js")

    assert not should_ignore("src/main.py")


def test_score_file_prefers_src_entrypoints():

    assert score_file("src/server.py") > score_file("docs/guide.md")


def test_score_file_language_hint_boost():

    assert score_file("src/app.py", "python") > score_file("docs/guide.md", "python")


def test_smart_pick_limits_count():

    paths = ["README.md", "src/main.py", "lib/core/handler.go", "tests/test_x.py"]

    picked = smart_pick_files(paths, 2)

    assert len(picked) == 2

    assert "tests/test_x.py" not in picked


def test_filter_blob_paths():

    tree = [
        {"type": "blob", "path": "src/app.py"},
        {"type": "tree", "path": "node_modules"},
        {"type": "blob", "path": "yarn.lock"},
    ]

    assert filter_blob_paths(tree) == ["src/app.py"]


def test_apply_subpath_filter():

    paths = ["src/a.py", "lib/b.py", "src/pkg/c.py"]

    assert apply_subpath_filter(paths, "src") == ["src/a.py", "src/pkg/c.py"]


def test_normalize_profile_fallback():

    assert normalize_profile("BRIEF") == "brief"

    assert normalize_profile("nope") == "standard"


def test_brief_profile_smaller_limits():

    brief = get_profile_limits("brief")

    standard = get_profile_limits("standard")

    assert brief.auto_files < standard.auto_files

    assert brief.pattern_source_files < standard.pattern_source_files


def test_compose_structure_chapters():

    paths = ["src/main.py"]

    chapters, text = compose_structure_chapters("o", "r", "main", paths, 1, get_profile_limits("standard"))

    assert len(chapters) >= 2

    assert chapters[0]["kind"] == "overview"

    assert chapters[1]["kind"] == "tree"

    assert "o/r" in text


def test_build_structure_text_truncation_note():

    paths = [f"file{i}.py" for i in range(600)]

    text = build_structure_text("o", "r", "main", paths, total_files=600)

    assert "500 of 600" in text

    assert "inspire_repo" in text or "inspire_repo_files" in text


@pytest.mark.asyncio
async def test_inspire_structure_success_with_chapters():

    tree = [{"type": "blob", "path": "src/main.py"}, {"type": "blob", "path": "README.md"}]

    ref = parse_github_url("https://github.com/o/r")

    assert ref is not None

    ctx = InspirationContext(
        ref=ref,
        branch="main",
        tree=tree,
        truncated=False,
        paths=filter_blob_paths(tree),
        profile="standard",
        limits=get_profile_limits("standard"),
        subpath=None,
        tree_cached=False,
    )

    service = RepoInspirationService(client=MagicMock(spec=GitHubInspirationClient))

    with patch.object(service, "_load_context", new_callable=AsyncMock) as load:
        load.return_value = ctx

        result = await service.inspire_structure("https://github.com/o/r")

    assert result["success"] is True

    assert "o/r" in result["data"]["text"]

    assert result["data"]["total_source_files"] == 2

    assert isinstance(result["data"]["chapters"], list)

    assert len(result["data"]["chapters"]) >= 2

    assert result["data"]["gitingest_url"].startswith("https://gitingest.com/")


@pytest.mark.asyncio
async def test_inspire_structure_invalid_url():

    service = RepoInspirationService()

    result = await service.inspire_structure("not-a-url")

    assert result["success"] is False


@pytest.mark.asyncio
async def test_inspire_repo_help():

    service = RepoInspirationService()

    result = await service.inspire_repo("help", "https://github.com/o/r")

    assert result["success"] is True

    assert "inspire_repo" in result["data"]["text"]

    assert result["data"]["chapters"][0]["kind"] == "prompt"


@pytest.mark.asyncio
async def test_tree_cache_reuse():

    get_tree_cache().clear()

    tree = [{"type": "blob", "path": "src/main.py"}]

    client = MagicMock(spec=GitHubInspirationClient)

    client.get_default_branch = AsyncMock(return_value="main")
    client.get_repo_meta = AsyncMock(return_value=None)
    client.get_tree = AsyncMock(return_value=(tree, False))

    service = RepoInspirationService(client=client)

    await service.inspire_structure("https://github.com/o/r")

    await service.inspire_patterns("https://github.com/o/r")

    assert client.get_tree.await_count == 1

    get_tree_cache().clear()


def test_is_large_repo_context():
    assert is_large_repo_context(truncated_github=True, path_count=10)
    assert is_large_repo_context(truncated_github=False, path_count=2500)
    assert not is_large_repo_context(truncated_github=False, path_count=100)


def test_infer_language_from_tree():
    tree = [{"type": "blob", "path": "pyproject.toml"}]
    assert infer_language_hint_from_tree(tree) == "python"


def test_suggest_subpaths_prefers_src():
    paths = [f"src/pkg/f{i}.py" for i in range(20)] + [f"docs/x{i}.md" for i in range(5)]
    subs = suggest_subpaths(paths, limit=3)
    assert subs[0] == "src"


def test_large_repo_structure_includes_directory_summary():
    paths = [f"pkg{a}/m{i}.py" for a in range(5) for i in range(500)]
    summary = build_directory_summary_text(paths)
    chapters, _ = compose_structure_chapters(
        "o",
        "r",
        "main",
        paths,
        len(paths),
        get_profile_limits("standard"),
        large_repo_mode=True,
        directory_summary=summary,
        study_hints=["Try subpath=pkg0"],
    )
    assert any(c["id"] == "dir-summary" for c in chapters)
