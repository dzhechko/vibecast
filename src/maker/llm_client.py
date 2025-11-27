"""
LLM Client Abstraction for MAKER

Provides a unified interface for different LLM providers,
with built-in support for MAKER's requirements:
- Temperature control
- Token limiting
- Response parsing
- Error handling
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
import logging

from .config import LLMConfig, LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    token_count: int
    finish_reason: str
    latency_ms: float
    model: str
    metadata: dict


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.call_count = 0
        self.total_tokens = 0
        self.total_latency_ms = 0

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    def get_stats(self) -> dict:
        """Get client statistics."""
        return {
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": self.total_latency_ms / max(1, self.call_count),
            "avg_tokens_per_call": self.total_tokens / max(1, self.call_count),
        }


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing and development."""

    def __init__(self, config: LLMConfig, responses: Optional[dict[str, str]] = None):
        super().__init__(config)
        self.responses = responses or {}
        self.default_response = "Mock response"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate mock response."""
        start_time = time.time()
        self.call_count += 1

        # Simulate latency
        await asyncio.sleep(0.01)

        # Find matching response
        content = self.default_response
        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                content = response
                break

        latency_ms = (time.time() - start_time) * 1000
        token_count = len(content.split())

        self.total_tokens += token_count
        self.total_latency_ms += latency_ms

        return LLMResponse(
            content=content,
            token_count=token_count,
            finish_reason="stop",
            latency_ms=latency_ms,
            model="mock",
            metadata={}
        )


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using OpenAI API."""
        start_time = time.time()
        self.call_count += 1

        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                model=kwargs.get("model", self.config.model),
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            )

            content = response.choices[0].message.content or ""
            token_count = response.usage.total_tokens if response.usage else len(content.split())
            finish_reason = response.choices[0].finish_reason or "unknown"

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

        latency_ms = (time.time() - start_time) * 1000
        self.total_tokens += token_count
        self.total_latency_ms += latency_ms

        return LLMResponse(
            content=content,
            token_count=token_count,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            model=self.config.model,
            metadata={"provider": "openai"}
        )


class AnthropicClient(BaseLLMClient):
    """Anthropic API client."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Anthropic API."""
        start_time = time.time()
        self.call_count += 1

        client = self._get_client()

        try:
            response = await client.messages.create(
                model=kwargs.get("model", self.config.model),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text if response.content else ""
            token_count = response.usage.input_tokens + response.usage.output_tokens
            finish_reason = response.stop_reason or "unknown"

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

        latency_ms = (time.time() - start_time) * 1000
        self.total_tokens += token_count
        self.total_latency_ms += latency_ms

        return LLMResponse(
            content=content,
            token_count=token_count,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            model=self.config.model,
            metadata={"provider": "anthropic"}
        )


class GoogleClient(BaseLLMClient):
    """Google Gemini API client."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """Lazy initialization of Google client."""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.config.api_key)
                self._client = genai.GenerativeModel(self.config.model)
            except ImportError:
                raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Google Gemini API."""
        start_time = time.time()
        self.call_count += 1

        client = self._get_client()

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        try:
            # Gemini's generate_content is synchronous, wrap it
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.generate_content(full_prompt)
            )

            content = response.text
            token_count = len(content.split())  # Approximation
            finish_reason = "stop"

        except Exception as e:
            logger.error(f"Google API error: {e}")
            raise

        latency_ms = (time.time() - start_time) * 1000
        self.total_tokens += token_count
        self.total_latency_ms += latency_ms

        return LLMResponse(
            content=content,
            token_count=token_count,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            model=self.config.model,
            metadata={"provider": "google"}
        )


def create_llm_client(config: LLMConfig) -> BaseLLMClient:
    """Factory function to create appropriate LLM client."""
    client_map = {
        LLMProvider.OPENAI: OpenAIClient,
        LLMProvider.ANTHROPIC: AnthropicClient,
        LLMProvider.GOOGLE: GoogleClient,
        LLMProvider.LOCAL: MockLLMClient,
    }

    client_class = client_map.get(config.provider, MockLLMClient)
    return client_class(config)
