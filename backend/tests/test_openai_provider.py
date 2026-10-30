"""Direct OpenAI integration tests; never call a paid API or use real keys."""
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from services.llm_providers import OpenAIClient
from services.postprocessing_service import PostProcessingService
from services.insight_service import InsightService


def completed_response():
    return {
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [
                {"type": "output_text", "text": '{"ok":'},
                {"type": "output_text", "text": 'true}'},
            ]},
        ],
        "usage": {"input_tokens": 110, "output_tokens": 45,
                  "output_tokens_details": {"reasoning_tokens": 30}},
    }


async def complete_with_handler(handler, model="gpt-6.1-sol"):
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with patch("services.llm_providers.openai.httpx.AsyncClient", return_value=http):
        return await OpenAIClient("test-openai-key").complete(
            "Clean this transcript as JSON", "Meeting text", model, 0.2,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gpt-6.1-sol", "gpt-6.1-terra", "gpt-6-luna", "gpt-6-astra"])
async def test_responses_request_and_reasoning_output(model):
    def handle(request):
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-openai-key"
        body = json.loads(request.content)
        assert body["model"] == model
        assert body["input"] == "Meeting text"
        assert "Clean this transcript" in body["instructions"]
        assert body["text"]["format"] == {"type": "json_object"}
        assert body["store"] is False
        assert "temperature" not in body
        return httpx.Response(200, json=completed_response())

    result = await complete_with_handler(handle, model)
    assert json.loads(result.text) == {"ok": True}
    assert (result.input_tokens, result.output_tokens) == (110, 45)


@pytest.mark.asyncio
async def test_custom_non_reasoning_model_keeps_temperature():
    def handle(request):
        assert json.loads(request.content)["temperature"] == 0.2
        return httpx.Response(200, json=completed_response())
    await complete_with_handler(handle, "gpt-4.1-mini")


@pytest.mark.asyncio
@pytest.mark.parametrize("data,error", [
    ({"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}, "max_output_tokens"),
    ({"status": "failed"}, "not completed"),
    ({"status": "completed", "output": []}, "no text"),
    ({"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal"}]}]}, "declined"),
])
async def test_unusable_responses_are_not_saved_as_success(data, error):
    with pytest.raises(ValueError, match=error):
        await complete_with_handler(lambda request: httpx.Response(200, json=data))


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 404])
async def test_permanent_api_errors_are_not_retried(status):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "Invalid request"}})
    with pytest.raises(httpx.HTTPStatusError):
        await complete_with_handler(handle)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [429, 503, "timeout"])
async def test_transient_failure_retried(failure):
    calls = []
    def handle(request):
        calls.append(request)
        if len(calls) == 1:
            if failure == "timeout":
                raise httpx.ReadTimeout("timeout", request=request)
            return httpx.Response(failure)
        return httpx.Response(200, json=completed_response())
    with patch("services.llm_providers.openai.asyncio.sleep", new_callable=AsyncMock):
        result = await complete_with_handler(handle)
    assert json.loads(result.text) == {"ok": True}
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_retry_budget_is_bounded():
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(503)
    with patch("services.llm_providers.openai.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(httpx.HTTPStatusError):
            await complete_with_handler(handle)
    assert len(calls) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("effort", ["default", "none", "low", "medium", "high", "xhigh", "max"])
async def test_reasoning_sent_only_when_explicit(effort):
    def handle(request):
        payload = json.loads(request.content)
        if effort == "default":
            assert "reasoning" not in payload
        else:
            assert payload["reasoning"] == {"effort": effort}
        return httpx.Response(200, json=completed_response())
    http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    with patch("services.llm_providers.openai.httpx.AsyncClient", return_value=http):
        await OpenAIClient("test-key").complete("JSON", "Text", "gpt-6-luna", reasoning_effort=effort)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gpt-6-astra", "gpt-6.1-sol"])
async def test_unsupported_none_reasoning_rejected_before_api_call(model):
    with pytest.raises(ValueError, match="does not support"):
        await OpenAIClient("test-key").complete("JSON", "Text", model, reasoning_effort="none")


@pytest.mark.asyncio
async def test_cleanup_then_insights_mindmap_with_direct_openai(tmp_path):
    from types import SimpleNamespace

    transcript = {"metadata": {}, "speakers": {}, "segments": [
        {"start": 0, "speaker": "SPEAKER_00", "text": "Обсудим проект"},
    ]}
    (tmp_path / "transcript.json").write_text(json.dumps(transcript))
    transcription = SimpleNamespace(id="test-meeting", filename="test.mp3",
                                    output_dir=str(tmp_path), initial_prompt=None)
    cleanup = PostProcessingService()
    insights = InsightService()
    cleanup.settings = cleanup.settings.model_copy(update={
        "openai_api_key": "test-key", "postprocessing_provider": "openai",
        "postprocessing_model": "gpt-6-luna", "postprocessing_reasoning_effort": "low",
    })
    insights.settings = insights.settings.model_copy(update={
        "openai_api_key": "test-key", "insights_provider": "openai",
        "insights_model": "gpt-6.1-sol", "insights_reasoning_effort": "high",
    })
    expected = [
        (cleanup, "low", "gpt-6-luna", {"segments": transcript["segments"], "speaker_suggestions": []}),
        (insights, "high", "gpt-6.1-sol", {"description": "Обсудили проект", "sections": [],
            "mindmap": {"format": "markdown", "content": "# Проект\n## Следующие шаги"}}),
    ]
    for service, effort, model, result in expected:
        def handle(request):
            body = json.loads(request.content)
            assert body["model"] == model
            assert body["reasoning"]["effort"] == effort
            assert "Обсудим проект" in body["input"]
            data = completed_response()
            data["output"] = [{"type": "message", "content": [
                {"type": "output_text", "text": json.dumps(result)},
            ]}]
            return httpx.Response(200, json=data)
        http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        with patch("services.llm_providers.openai.httpx.AsyncClient", return_value=http):
            if service is cleanup:
                await service.process_transcript(transcription, "it-meeting")
            else:
                output = await service.generate_insights(transcription, "it-meeting", source="cleaned")
                assert output.mindmap["content"].startswith("# Проект")
                assert output.cost_usd == pytest.approx((110 * 2 + 45 * 10) / 1_000_000)

    cleaned = json.loads((tmp_path / "transcript_cleaned.json").read_text())
    analysis = json.loads((tmp_path / "insights_it-meeting.json").read_text())
    assert cleaned["metadata"]["provider"] == "openai"
    assert analysis["metadata"]["provider"] == "openai"
    assert analysis["metadata"]["source"] == "cleaned"
    assert analysis["stats"]["output_tokens"] == 45


@pytest.mark.parametrize("service_class", [PostProcessingService, InsightService])
def test_both_ai_features_require_the_openai_key(service_class):
    service = service_class()
    service.settings = service.settings.model_copy(update={"openai_api_key": None})
    with pytest.raises(ValueError, match="OpenAI API key not configured"):
        service._get_client("openai")
    service.settings = service.settings.model_copy(update={"openai_api_key": "test-key"})
    client = service._get_client("openai")
    assert isinstance(client, OpenAIClient)
    assert client.api_key == "test-key"
