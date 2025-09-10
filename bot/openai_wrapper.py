#!/usr/bin/env python3
"""
Async OpenAI Client Wrapper
Provides a safe, async interface for OpenAI API calls with error handling and retries.
Enhanced with circuit breaker and resource management for improved reliability.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp


try:
    from .circuit_breaker import (
        CircuitBreakerError,
        circuit_manager,
        create_ai_service_circuit_config,
    )
    from .resource_manager import get_http_session
except ImportError:
    # Fallback for direct execution
    from circuit_breaker import (
        CircuitBreakerError,
        circuit_manager,
        create_ai_service_circuit_config,
    )
    from resource_manager import get_http_session


logger = logging.getLogger(__name__)


class OpenAIWrapper:
    """Async wrapper for OpenAI API calls with error handling and rate limiting."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        max_retries: int = 3,
        timeout: float = 30.0,
        rate_limit_requests_per_minute: int = 60,
        enable_circuit_breaker: bool = True,
    ):
        """Initialize OpenAI wrapper with enhanced reliability features."""
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout = timeout
        self.rate_limit_rpm = rate_limit_requests_per_minute
        self.enable_circuit_breaker = enable_circuit_breaker

        # Legacy compatibility
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0
        self._min_request_interval = (
            60.0 / rate_limit_requests_per_minute
        )  # Dynamic based on RPM

        # Rate limiting
        self._request_count = 0
        self._minute_start = time.time()

        # Circuit breaker for reliability
        if self.enable_circuit_breaker:
            config = create_ai_service_circuit_config(timeout=timeout)
            self._circuit_breaker = circuit_manager.get_breaker("openai_api", config)
        else:
            self._circuit_breaker = None

        # Request statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "circuit_breaker_trips": 0,
            "rate_limit_hits": 0,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure aiohttp session is created using resource manager."""
        if self.session is None or self.session.closed:
            # Use resource manager for session handling
            try:
                self.session = await get_http_session(
                    key="openai_client",
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Project-Automation-Bot/1.0",
                    },
                )
            except Exception as e:
                logger.error(f"Failed to create HTTP session: {e}")
                # Fallback to direct session creation
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                self.session = aiohttp.ClientSession(
                    timeout=timeout,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Project-Automation-Bot/1.0",
                    },
                )

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _rate_limit(self):
        """Enhanced rate limiting with minute-based tracking."""
        current_time = time.time()

        # Reset counter if a minute has passed
        if current_time - self._minute_start >= 60:
            self._request_count = 0
            self._minute_start = current_time

        # Check if we've hit the rate limit
        if self._request_count >= self.rate_limit_rpm:
            wait_time = 60 - (current_time - self._minute_start)
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                self._stats["rate_limit_hits"] += 1
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._minute_start = time.time()

        # Ensure minimum interval between requests
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last)

        self._last_request_time = time.time()
        self._request_count += 1

    async def _make_request_internal(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Internal method to make HTTP request."""
        await self._ensure_session()
        await self._rate_limit()

        url = f"{self.base_url}/{endpoint}"
        self._stats["total_requests"] += 1

        async with self.session.post(url, json=data) as response:
            response_text = await response.text()

            if response.status == 200:
                self._stats["successful_requests"] += 1
                return json.loads(response_text)
            elif response.status == 429:  # Rate limited
                self._stats["rate_limit_hits"] += 1
                logger.warning(f"OpenAI rate limited: {response_text}")
                raise aiohttp.ClientError(f"Rate limited: {response_text}")
            elif response.status >= 500:  # Server error
                logger.warning(
                    f"OpenAI server error {response.status}: {response_text}"
                )
                raise aiohttp.ClientError(
                    f"Server error {response.status}: {response_text}"
                )
            else:
                self._stats["failed_requests"] += 1
                logger.error(f"OpenAI API error {response.status}: {response_text}")
                raise aiohttp.ClientError(
                    f"API error {response.status}: {response_text}"
                )

    async def _make_request(
        self, endpoint: str, data: Dict[str, Any], retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """Make an async HTTP request to OpenAI API with circuit breaker and retries."""
        if self._circuit_breaker:
            try:
                return await self._circuit_breaker.call(
                    self._make_request_internal, endpoint, data
                )
            except CircuitBreakerError:
                self._stats["circuit_breaker_trips"] += 1
                logger.error("OpenAI API circuit breaker is open")
                return None
        else:
            # Fallback to original retry logic without circuit breaker
            for attempt in range(retries):
                try:
                    return await self._make_request_internal(endpoint, data)
                except Exception as e:
                    if attempt == retries - 1:
                        self._stats["failed_requests"] += 1
                        logger.error(
                            f"OpenAI request failed after {retries} attempts: {e}"
                        )
                        return None
                    else:
                        wait_time = min(2**attempt, 10)
                        logger.warning(
                            f"OpenAI request failed, retrying in {wait_time}s: {e}"
                        )
                        await asyncio.sleep(wait_time)

        return None

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """
        Generate a chat completion using OpenAI API.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: OpenAI model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Generated text response or None if failed
        """
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        result = await self._make_request("chat/completions", data)

        if result and "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"].strip()

        return None

    async def summarize_text(self, text: str, max_length: int = 200) -> Optional[str]:
        """
        Summarize the given text using OpenAI.

        Args:
            text: Text to summarize
            max_length: Maximum length of summary

        Returns:
            Summary text or None if failed
        """
        if len(text) < 100:  # Don't summarize very short text
            return text

        messages = [
            {
                "role": "system",
                "content": f"Summarize the following text in {max_length} characters or less. Focus on key points and main topics.",
            },
            {
                "role": "user",
                "content": text[:4000],  # Limit input to avoid token limits
            },
        ]

        return await self.chat_completion(messages, max_tokens=max_length // 3)

    async def answer_question(self, question: str, context: str = "") -> Optional[str]:
        """
        Answer a question using OpenAI, optionally with context.

        Args:
            question: Question to answer
            context: Optional context to help answer the question

        Returns:
            Answer text or None if failed
        """
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant for a software development team. Provide clear, concise answers.",
            }
        ]

        if context:
            messages.append(
                {
                    "role": "user",
                    "content": f"Context: {context[:2000]}\n\nQuestion: {question}",
                }
            )
        else:
            messages.append({"role": "user", "content": question})

        return await self.chat_completion(messages, max_tokens=400)

    def get_stats(self) -> Dict[str, Any]:
        """Get OpenAI wrapper statistics."""
        return {
            "total_requests": self._stats["total_requests"],
            "successful_requests": self._stats["successful_requests"],
            "failed_requests": self._stats["failed_requests"],
            "circuit_breaker_trips": self._stats["circuit_breaker_trips"],
            "rate_limit_hits": self._stats["rate_limit_hits"],
            "success_rate": self._stats["successful_requests"]
            / max(1, self._stats["total_requests"]),
            "failure_rate": self._stats["failed_requests"]
            / max(1, self._stats["total_requests"]),
            "circuit_breaker_enabled": self.enable_circuit_breaker,
            "rate_limit_rpm": self.rate_limit_rpm,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of OpenAI wrapper."""
        stats = self.get_stats()

        # Determine health status
        if self._circuit_breaker:
            circuit_stats = self._circuit_breaker.get_stats()
            circuit_state = circuit_stats["state"]

            if circuit_state == "open":
                status = "critical"
                message = "Circuit breaker is open"
            elif circuit_state == "half_open":
                status = "warning"
                message = "Circuit breaker is testing recovery"
            elif stats["failure_rate"] > 0.5:
                status = "warning"
                message = f"High failure rate: {stats['failure_rate']:.1%}"
            else:
                status = "healthy"
                message = "Operating normally"

            return {
                "status": status,
                "message": message,
                "stats": stats,
                "circuit_breaker": circuit_stats,
            }
        else:
            if stats["failure_rate"] > 0.7:
                status = "critical"
                message = f"Very high failure rate: {stats['failure_rate']:.1%}"
            elif stats["failure_rate"] > 0.3:
                status = "warning"
                message = f"High failure rate: {stats['failure_rate']:.1%}"
            else:
                status = "healthy"
                message = "Operating normally"

            return {
                "status": status,
                "message": message,
                "stats": stats,
                "circuit_breaker": None,
            }
