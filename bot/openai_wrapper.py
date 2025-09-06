#!/usr/bin/env python3
"""
Async OpenAI Client Wrapper
Provides a safe, async interface for OpenAI API calls with error handling and retries.
"""

import asyncio
import aiohttp
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import time


logger = logging.getLogger(__name__)


class OpenAIWrapper:
    """Async wrapper for OpenAI API calls with error handling and rate limiting."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Minimum seconds between requests
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "proj-automation-bot/1.0"
                }
            )
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _rate_limit(self):
        """Simple rate limiting to avoid hitting API limits."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last)
        self._last_request_time = time.time()
    
    async def _make_request(self, endpoint: str, data: Dict[str, Any], retries: int = 3) -> Optional[Dict[str, Any]]:
        """Make an async HTTP request to OpenAI API with retries."""
        await self._ensure_session()
        await self._rate_limit()
        
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(retries):
            try:
                async with self.session.post(url, json=data) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        return json.loads(response_text)
                    elif response.status == 429:  # Rate limited
                        wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                        logger.warning(f"OpenAI rate limited, waiting {wait_time}s before retry {attempt + 1}")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status >= 500:  # Server error
                        wait_time = min(2 ** attempt, 5)
                        logger.warning(f"OpenAI server error {response.status}, retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"OpenAI API error {response.status}: {response_text}")
                        return None
                        
            except asyncio.TimeoutError:
                logger.warning(f"OpenAI request timeout, attempt {attempt + 1}")
                if attempt == retries - 1:
                    logger.error("OpenAI request failed after all retries due to timeout")
                    return None
            except Exception as e:
                logger.error(f"OpenAI request error: {e}")
                if attempt == retries - 1:
                    return None
                await asyncio.sleep(1)
        
        return None
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 500,
        temperature: float = 0.7
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
            "temperature": temperature
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
                "content": f"Summarize the following text in {max_length} characters or less. Focus on key points and main topics."
            },
            {
                "role": "user", 
                "content": text[:4000]  # Limit input to avoid token limits
            }
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
                "content": "You are a helpful assistant for a software development team. Provide clear, concise answers."
            }
        ]
        
        if context:
            messages.append({
                "role": "user",
                "content": f"Context: {context[:2000]}\n\nQuestion: {question}"
            })
        else:
            messages.append({
                "role": "user",
                "content": question
            })
        
        return await self.chat_completion(messages, max_tokens=400)