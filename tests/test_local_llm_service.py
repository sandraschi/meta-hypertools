"""Tests for local LLM API bridge (mocked HTTP)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meta_mcp.services.local_llm_service import LocalLLMService


@pytest.mark.asyncio
async def test_list_models_ollama_shape():
    service = LocalLLMService()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"models": [{"name": "qwen2.5:7b"}]})

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp)))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service.list_models("ollama", "http://localhost:11434")

    assert result["success"] is True
    assert result["data"]["models"][0]["id"] == "qwen2.5:7b"
