"""Model-agnostic LLM client using LiteLLM for judge evaluation and synthetic generation."""

import asyncio
from typing import Any

import litellm
import structlog
from litellm import acompletion, completion_cost

from evalforge.config import get_settings

logger = structlog.get_logger(__name__)

# Suppress noisy LiteLLM logs in standard runs
litellm.suppress_debug_info = True


class LiteLLMClient:
    """Wrapper around LiteLLM providing unified completion, token cost calculation, and retries."""

    def __init__(self, default_model: str | None = None) -> None:
        settings = get_settings()
        self.default_model = default_model or settings.judge_model

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> tuple[str, float, int]:
        """Executes an async completion call with automatic retries and cost tracking.

        Args:
            messages: List of OpenAI-format message dictionaries.
            model: Optional model identifier (defaults to default_model).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            response_format: Optional schema enforcement dict (e.g. {"type": "json_object"}).
            max_retries: Number of retry attempts on rate limit / transient errors.
            **kwargs: Extra parameters passed to litellm.acompletion.

        Returns:
            Tuple of (response_text, cost_usd, total_tokens).
        """
        selected_model = model or self.default_model
        attempt = 0
        last_err: Exception | None = None

        while attempt < max_retries:
            try:
                params: dict[str, Any] = {
                    "model": selected_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs,
                }
                if response_format:
                    params["response_format"] = response_format

                response = await acompletion(**params)

                content = response.choices[0].message.content or ""
                try:
                    cost = completion_cost(completion_response=response)
                except Exception:
                    cost = 0.0

                usage = getattr(response, "usage", None)
                total_tokens = usage.total_tokens if usage else 0

                return content, float(cost or 0.0), total_tokens

            except Exception as exc:
                last_err = exc
                attempt += 1
                wait_time = 2**attempt
                logger.warning(
                    "LLM completion attempt failed",
                    model=selected_model,
                    attempt=attempt,
                    error=str(exc),
                    retry_in=wait_time,
                )
                if attempt < max_retries:
                    await asyncio.sleep(wait_time)

        logger.error(
            "LLM completion exhausted all retries",
            model=selected_model,
            error=str(last_err),
        )
        raise RuntimeError(
            f"Failed LLM completion after {max_retries} attempts: {last_err}"
        ) from last_err


_client_instance: LiteLLMClient | None = None


def get_llm_client(default_model: str | None = None) -> LiteLLMClient:
    """Get or instantiate singleton LiteLLMClient."""
    global _client_instance
    if _client_instance is None or (
        default_model and _client_instance.default_model != default_model
    ):
        _client_instance = LiteLLMClient(default_model=default_model)
    return _client_instance
