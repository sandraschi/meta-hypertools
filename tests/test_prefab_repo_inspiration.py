"""Tests for repo inspiration Prefab card builder."""

from meta_mcp.prefabs.repo_inspiration import build_inspire_structure_card


def test_build_inspire_structure_card_success():
    result = {
        "success": True,
        "message": "Structure for acme/widget@main",
        "data": {
            "owner": "acme",
            "repo": "widget",
            "branch": "main",
            "profile": "standard",
            "total_source_files": 120,
            "shown_files": 50,
            "tree_cached": True,
            "large_repo_mode": False,
            "tree_truncated_by_github": False,
            "rate_limit_remaining": 42,
            "text": "overview line",
        },
    }
    card = build_inspire_structure_card(result)
    assert card.type == "Card"
    assert len(card.children) >= 2
    header = card.children[0]
    assert header.type == "CardHeader"


def test_build_inspire_structure_card_large_repo():
    result = {
        "data": {
            "owner": "big",
            "repo": "mono",
            "branch": "dev",
            "profile": "brief",
            "subpath": "packages/core",
            "total_source_files": 9000,
            "shown_files": 120,
            "large_repo_mode": True,
            "tree_truncated_by_github": True,
            "hints": ["Use subpath=packages/core", "Try gitingest for full tree"],
        }
    }
    card = build_inspire_structure_card(result)
    assert card.type == "Card"
    assert card.css_class == "max-w-lg"
