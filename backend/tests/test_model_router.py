"""
Tests for ModelRouter and LlmService nano routing.

All Azure OpenAI calls are mocked; no real credentials needed.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.services.llm_service import LlmService, LLMResponse
from app.services.model_router import ModelRouter, TIER_1_MODEL, TIER_2_MODEL, TIER_3_MODEL
from app.models.schemas import ModelRouterResponse


# ── LLMResponse ───────────────────────────────────────────────────────────────


def test_llm_response_fields():
    resp = LLMResponse(
        content="photosynthesis converts light to energy",
        model="gpt-4.1-nano",
        tokens_input=20,
        tokens_output=10,
        finish_reason="stop",
    )
    assert resp.tokens_input == 20
    assert resp.tokens_output == 10
    assert resp.finish_reason == "stop"


# ── LlmService.classify_query ─────────────────────────────────────────────────


@pytest.fixture
def llm_service():
    svc = LlmService.__new__(LlmService)
    svc.settings = MagicMock()
    svc.settings.AZURE_OPENAI_NANO_DEPLOYMENT = "gpt-4.1-nano"
    svc.settings.AZURE_OPENAI_MINI_DEPLOYMENT = "gpt-4.1-mini"
    svc.settings.AZURE_OPENAI_FULL_DEPLOYMENT = "gpt-4.1"
    svc._client = AsyncMock()
    return svc


def _make_openai_response(content: str, prompt_tokens: int = 20, completion_tokens: int = 5) -> MagicMock:
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens

    choice = MagicMock()
    choice.message.content = content
    choice.finish_reason = "stop"

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


@pytest.mark.asyncio
async def test_classify_query_returns_simple(llm_service):
    llm_service._client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("SIMPLE")
    )
    result = await llm_service.classify_query("What is photosynthesis?")
    assert result == "simple"


@pytest.mark.asyncio
async def test_classify_query_returns_medium(llm_service):
    llm_service._client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("MEDIUM")
    )
    result = await llm_service.classify_query("Why does the sky appear blue?")
    assert result == "medium"


@pytest.mark.asyncio
async def test_classify_query_returns_complex(llm_service):
    llm_service._client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("COMPLEX")
    )
    result = await llm_service.classify_query("Integrate x^2 + sin(x) from 0 to pi")
    assert result == "complex"


@pytest.mark.asyncio
async def test_classify_query_defaults_medium_on_failure(llm_service):
    llm_service._client.chat.completions.create = AsyncMock(side_effect=RuntimeError("API down"))
    result = await llm_service.classify_query("Any question")
    assert result == "medium"


# ── LlmService.call_nano uses NANO deployment ─────────────────────────────────


@pytest.mark.asyncio
async def test_call_nano_uses_nano_deployment(llm_service):
    llm_service._client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("answer", prompt_tokens=50, completion_tokens=30)
    )
    resp = await llm_service.call_nano([{"role": "user", "content": "hi"}])
    call_kwargs = llm_service._client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "gpt-4.1-nano"
    assert resp.tokens_input == 50
    assert resp.tokens_output == 30


@pytest.mark.asyncio
async def test_call_mini_uses_mini_deployment(llm_service):
    llm_service._client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("answer", prompt_tokens=100, completion_tokens=40)
    )
    resp = await llm_service.call_mini([{"role": "user", "content": "explain gravity"}])
    call_kwargs = llm_service._client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "gpt-4.1-mini"
    assert resp.tokens_input == 100


@pytest.mark.asyncio
async def test_call_full_uses_full_deployment(llm_service):
    llm_service._client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("proof", prompt_tokens=200, completion_tokens=150)
    )
    resp = await llm_service.call_full([{"role": "user", "content": "prove fundamental theorem"}])
    call_kwargs = llm_service._client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "gpt-4.1"


# ── LlmService.translate_to_english ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_translate_to_english_success(llm_service):
    llm_service._client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("What is photosynthesis?")
    )
    result = await llm_service.translate_to_english("Pranalipi kya hai?")
    assert result == "What is photosynthesis?"


@pytest.mark.asyncio
async def test_translate_to_english_returns_raw_on_failure(llm_service):
    llm_service._client.chat.completions.create = AsyncMock(side_effect=RuntimeError("API down"))
    original = "Pranalipi kya hai?"
    result = await llm_service.translate_to_english(original)
    assert result == original


# ── ModelRouter tier selection ─────────────────────────────────────────────────


@pytest.fixture
def mock_router():
    router = ModelRouter.__new__(ModelRouter)
    router.openai_client = AsyncMock()
    router.llm_service = AsyncMock()
    router.cache_service = AsyncMock()
    router.cosmos_repo = AsyncMock()
    router.breaker = MagicMock()
    router.breaker.is_tripped = MagicMock(return_value=False)
    router.breaker.log_failure = MagicMock()
    return router


@pytest.mark.asyncio
async def test_simple_query_routes_to_tier_1(mock_router):
    """SIMPLE classification → TIER_1_MODEL (nano) in metadata."""
    mock_router.cache_service.check_cache = AsyncMock(return_value=None)
    mock_router.llm_service.call_nano = AsyncMock(
        return_value=LLMResponse(
            content="SIMPLE",
            model=TIER_1_MODEL,
            tokens_input=15,
            tokens_output=3,
            finish_reason="stop",
        )
    )
    mock_router.cosmos_repo.log_query_usage = AsyncMock()

    # Build a fake streaming response that includes usage
    chunk_content = MagicMock()
    chunk_content.choices = [MagicMock()]
    chunk_content.choices[0].delta.content = "Photosynthesis is..."
    chunk_content.usage = None

    chunk_usage = MagicMock()
    chunk_usage.choices = []
    chunk_usage.usage = MagicMock()
    chunk_usage.usage.prompt_tokens = 80
    chunk_usage.usage.completion_tokens = 40

    async def _fake_stream(*args, **kwargs):
        yield chunk_content
        yield chunk_usage

    mock_router.openai_client.chat.completions.create = AsyncMock(return_value=_fake_stream())

    chunks = []
    async for c in mock_router.route_query_stream(
        query="What is photosynthesis?",
        board="cbse",
        class_level=8,
        subject="science",
        context="",
        confidence="high",
        system_prompt="You are a helpful teacher.",
    ):
        chunks.append(c)

    metadata_chunk = next(c for c in chunks if "[METADATA]" in c)
    meta = json.loads(metadata_chunk.replace("\n\n[METADATA]", ""))
    assert meta["model_used"] == TIER_1_MODEL
    assert meta["tier"] == 1
    assert meta["from_cache"] is False
    assert meta["tokens_input"] == 80
    assert meta["tokens_output"] == 40
    assert meta["tokens_total"] == 120
    assert meta["classification_tokens"] == 18   # 15 + 3


@pytest.mark.asyncio
async def test_image_query_routes_to_tier_2(mock_router):
    """has_image=True forces MEDIUM → TIER_2_MODEL without calling classifier."""
    mock_router.cache_service.check_cache = AsyncMock(return_value=None)
    mock_router.cosmos_repo.log_query_usage = AsyncMock()

    chunk_content = MagicMock()
    chunk_content.choices = [MagicMock()]
    chunk_content.choices[0].delta.content = "The answer is 42."
    chunk_content.usage = None

    chunk_usage = MagicMock()
    chunk_usage.choices = []
    chunk_usage.usage = MagicMock()
    chunk_usage.usage.prompt_tokens = 120
    chunk_usage.usage.completion_tokens = 20

    async def _fake_stream(*args, **kwargs):
        yield chunk_content
        yield chunk_usage

    mock_router.openai_client.chat.completions.create = AsyncMock(return_value=_fake_stream())

    chunks = []
    async for c in mock_router.route_query_stream(
        query="Solve this",
        board="cbse",
        class_level=10,
        subject="maths",
        context="",
        confidence="none",
        system_prompt="You are a teacher.",
        has_image=True,
    ):
        chunks.append(c)

    metadata_chunk = next(c for c in chunks if "[METADATA]" in c)
    meta = json.loads(metadata_chunk.replace("\n\n[METADATA]", ""))
    assert meta["tier"] == 2
    assert meta["model_used"] == TIER_2_MODEL
    assert meta["classification_tokens"] == 0   # skipped because has_image


@pytest.mark.asyncio
async def test_complex_query_routes_to_tier_3(mock_router):
    """COMPLEX classification → TIER_3_MODEL (full) in metadata."""
    mock_router.cache_service.check_cache = AsyncMock(return_value=None)
    mock_router.llm_service.call_nano = AsyncMock(
        return_value=LLMResponse(
            content="COMPLEX",
            model=TIER_1_MODEL,
            tokens_input=30,
            tokens_output=4,
            finish_reason="stop",
        )
    )
    mock_router.cosmos_repo.log_query_usage = AsyncMock()

    chunk_content = MagicMock()
    chunk_content.choices = [MagicMock()]
    chunk_content.choices[0].delta.content = "Proof: ..."
    chunk_content.usage = None

    chunk_usage = MagicMock()
    chunk_usage.choices = []
    chunk_usage.usage = MagicMock()
    chunk_usage.usage.prompt_tokens = 500
    chunk_usage.usage.completion_tokens = 300

    async def _fake_stream(*args, **kwargs):
        yield chunk_content
        yield chunk_usage

    mock_router.openai_client.chat.completions.create = AsyncMock(return_value=_fake_stream())

    chunks = []
    async for c in mock_router.route_query_stream(
        query="Prove that the integral of e^x is e^x",
        board="cbse",
        class_level=12,
        subject="mathematics",
        context="",
        confidence="medium",
        system_prompt="You are a teacher.",
    ):
        chunks.append(c)

    metadata_chunk = next(c for c in chunks if "[METADATA]" in c)
    meta = json.loads(metadata_chunk.replace("\n\n[METADATA]", ""))
    assert meta["tier"] == 3
    assert meta["model_used"] == TIER_3_MODEL
    assert meta["total_billable_tokens"] == 500 + 300 + 30 + 4


@pytest.mark.asyncio
async def test_cache_hit_returns_tier_0(mock_router):
    """Cache hit → tier=0, no LLM cost, tokens all zero."""
    cached = MagicMock()
    cached.answers = {"en": "Photosynthesis is the process..."}
    cached.source_citation = "NCERT Class 7 Science Ch. 1"
    mock_router.cache_service.check_cache = AsyncMock(return_value=cached)

    chunks = []
    async for c in mock_router.route_query_stream(
        query="What is photosynthesis?",
        board="cbse",
        class_level=7,
        subject="science",
        context="",
        confidence="high",
        system_prompt="You are a teacher.",
    ):
        chunks.append(c)

    metadata_chunk = next(c for c in chunks if "[METADATA]" in c)
    meta = json.loads(metadata_chunk.replace("\n\n[METADATA]", ""))
    assert meta["tier"] == 0
    assert meta["from_cache"] is True
    assert meta["tokens_total"] == 0
    assert meta["total_billable_tokens"] == 0
    assert meta["model_used"] == "cache"
    assert len(meta["sources"]) == 1
    assert meta["sources"][0]["title"] == "NCERT Class 7 Science Ch. 1"


@pytest.mark.asyncio
async def test_force_complex_bypass_classifier(mock_router):
    """Force-complex keyword in subject skips the classifier call."""
    mock_router.cache_service.check_cache = AsyncMock(return_value=None)
    mock_router.cosmos_repo.log_query_usage = AsyncMock()

    chunk_content = MagicMock()
    chunk_content.choices = [MagicMock()]
    chunk_content.choices[0].delta.content = "Integration..."
    chunk_content.usage = None

    chunk_usage = MagicMock()
    chunk_usage.choices = []
    chunk_usage.usage = MagicMock()
    chunk_usage.usage.prompt_tokens = 200
    chunk_usage.usage.completion_tokens = 100

    async def _fake_stream(*args, **kwargs):
        yield chunk_content
        yield chunk_usage

    mock_router.openai_client.chat.completions.create = AsyncMock(return_value=_fake_stream())

    chunks = []
    async for c in mock_router.route_query_stream(
        query="solve integration of x^2 dx",
        board="cbse",
        class_level=12,
        subject="mathematics",
        context="",
        confidence="low",
        system_prompt="You are a teacher.",
    ):
        chunks.append(c)

    metadata_chunk = next(c for c in chunks if "[METADATA]" in c)
    meta = json.loads(metadata_chunk.replace("\n\n[METADATA]", ""))
    assert meta["tier"] == 3
    assert meta["classification_tokens"] == 0   # no classifier call made
    mock_router.llm_service.call_nano.assert_not_called()
