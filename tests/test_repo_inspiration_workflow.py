"""Tests for inspire_repo_workflow helpers."""

from meta_mcp.utils.repo_inspiration_workflow import (
    parse_paths_from_sampling,
    pick_paths_deterministic,
)


def test_pick_paths_with_subpath_hint():
    paths = [f"src/a{i}.py" for i in range(10)] + [f"docs/b{i}.md" for i in range(5)]
    picked = pick_paths_deterministic(paths, max_paths=3, suggested_subpaths=["src"])
    assert all(p.startswith("src/") for p in picked)
    assert len(picked) == 3


def test_parse_paths_from_sampling():
    valid = {"src/main.py", "lib/util.py"}
    text = "Study these:\nsrc/main.py\nlib/util.py\n"
    assert parse_paths_from_sampling(text, valid) == ["src/main.py", "lib/util.py"]
