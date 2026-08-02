from unittest.mock import patch

from meta_mcp.tools.mcp_repo_analyzer import (
    _analyze_repo,
    _classify_zoo_animal,
    _evaluate_runt_status,
)


def test_analyze_repo_invalid_path(tmp_path):
    # An empty directory is not an MCP repo (no reqs/pyproject)
    result = _analyze_repo(tmp_path)
    assert result is None


def test_classify_zoo_animal():
    # Jumbo
    info = {"name": "my-postgres-mcp", "tool_count": 5}
    _classify_zoo_animal(info)
    assert info["zoo_class"] == "jumbo"
    assert info["zoo_animal"] == ""

    # Large
    info = {"name": "complex-mcp", "tool_count": 12}
    _classify_zoo_animal(info)
    assert info["zoo_class"] == "large"
    assert info["zoo_animal"] == ""

    # Chipmunk
    info = {"name": "simple-echo-tool", "tool_count": 1}
    _classify_zoo_animal(info)
    assert info["zoo_class"] == "chipmunk"
    assert info["zoo_animal"] == ""


@patch("meta_mcp.tools.mcp_repo_analyzer.evaluate_rules")
def test_evaluate_runt_status(mock_evaluate):
    # Mock the rule evaluation to return predictable results
    mock_evaluate.return_value = {
        "is_runt": True,
        "runt_reasons": ["Old FastMCP"],
        "recommendations": ["Upgrade"],
        "violation_count": 1,
        "critical_count": 1,
        "violations": [],
        "critical_violations": [],
        "score_deduction": 10,
    }

    info = {"name": "test-repo"}
    _evaluate_runt_status(info, "2.0.0")

    assert info["is_runt"] is True
    assert info["status_label"] == "Minor Runt"  # Critical count 1 < 3
    assert info["fastmcp_version"] == "2.0.0"


@patch("meta_mcp.tools.mcp_repo_analyzer.evaluate_rules")
def test_evaluate_sota_status(mock_evaluate):
    # Mock SOTA result
    mock_evaluate.return_value = {
        "is_runt": False,
        "runt_reasons": [],
        "recommendations": [],
        "violation_count": 0,
        "critical_count": 0,
        "violations": [],
        "critical_violations": [],
        "score_deduction": 0,
    }

    info = {"name": "sota-repo"}
    _evaluate_runt_status(info, "2.14.0")

    assert info["is_runt"] is False
    assert info["status_label"] == "SOTA"
    assert info["status_emoji"] == "SUCCESS"
