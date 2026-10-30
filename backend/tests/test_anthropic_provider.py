"""Anthropic wire protocol, structured outputs and thinking compatibility."""
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from services.llm_providers import AnthropicClient
from services.llm_providers.anthropic import RESPONSE_SCHEMAS


def completed_response():
    return {"stop_reason": "end_turn", "content": [
        {"type": "thinking", "thinking": "Not transcript text", "signature": "test"},
        {"type": "text", "text": '{"segments": [], "speaker_suggestions": []}'},
    ], "usage": {"input_tokens": 100, "output_tokens": 50}}


async def run_client(handler, **kwargs):
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with patch("services.llm_providers.anthropic.httpx.AsyncClient", return_value=http):
        return await AnthropicClient("test-secret").complete(
            "Clean as JSON", "Meeting text", "claude-haiku-5-5", **kwargs,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ["cleanup", "speakers", "insights"])
@pytest.mark.parametrize("effort", ["default", "none", "low", "medium", "high", "xhigh", "max"])
async def test_messages_payload_schema_and_thinking(task, effort):
    def handle(request):
        assert str(request.url) == "https://api.anthropic.com/v1/messages"
        assert request.headers["x-api-key"] == "test-secret"
        assert request.headers["anthropic-version"] == "2023-06-01"
        assert "authorization" not in request.headers
        body = json.loads(request.content)
        assert body["model"] == "claude-haiku-5-5"
        assert body["messages"] == [{"role": "user", "content": "Meeting text"}]
        assert body["max_tokens"] == 128000
        assert body["output_config"]["format"] == {"type": "json_schema", "schema": RESPONSE_SCHEMAS[task]}
        assert "temperature" not in body
        if effort == "default":
            assert "thinking" not in body
            assert "effort" not in body["output_config"]
        elif effort == "none":
            assert body["thinking"] == {"type": "disabled"}
            assert "effort" not in body["output_config"]
        else:
            assert body["thinking"] == {"type": "adaptive"}
            assert body["output_config"]["effort"] == effort
        return httpx.Response(200, json=completed_response())
    result = await run_client(handle, reasoning_effort=effort, task=task)
    assert "Not transcript text" not in result.text
    assert json.loads(result.text)["segments"] == []
    assert (result.input_tokens, result.output_tokens) == (100, 50)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1"])
async def test_none_reasoning_not_offered_for_always_thinking_models(model):
    with pytest.raises(ValueError, match="does not support disabling"):
        await AnthropicClient("test").complete("JSON", "Text", model, reasoning_effort="none")


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["max_tokens", "refusal", "tool_use", "pause_turn"])
async def test_incomplete_or_refused_not_accepted(reason):
    data = completed_response()
    data["stop_reason"] = reason
    with pytest.raises(ValueError, match=reason):
        await run_client(lambda request: httpx.Response(200, json=data))


@pytest.mark.asyncio
async def test_thinking_only_not_accepted():
    data = completed_response()
    data["content"] = [{"type": "thinking", "thinking": "Hidden"}]
    with pytest.raises(ValueError, match="no text"):
        await run_client(lambda request: httpx.Response(200, json=data))


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [429, 529, "timeout"])
async def test_transient_failure_retried(failure):
    calls = []
    def handle(request):
        calls.append(request)
        if len(calls) == 1:
            if failure == "timeout":
                raise httpx.ReadTimeout("timeout", request=request)
            return httpx.Response(failure)
        return httpx.Response(200, json=completed_response())
    with patch("services.llm_providers.anthropic.asyncio.sleep", new_callable=AsyncMock):
        await run_client(handle)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_invalid_api_key_not_retried():
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(401)
    with pytest.raises(httpx.HTTPStatusError):
        await run_client(handle)
    assert len(calls) == 1
