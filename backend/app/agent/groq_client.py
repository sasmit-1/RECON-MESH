"""
TRIDENT Groq Provider (Step 07)
Provides sub-200ms ultra-low-latency Groq LPU inference.
"""

import json
from typing import AsyncGenerator
import httpx

from backend.app.agent.base_provider import BaseLLMEngine


class GroqLLM(BaseLLMEngine):
    """
    Groq LPU REST client provider.
    """

    def __init__(self, api_key: str = "", model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    async def generate_resolution(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            return json.dumps({
                "hypothesis": "Groq API key not configured (GROQ_API_KEY missing).",
                "discrepancy_type": "UNCONFIGURED_API_KEY",
                "ast_math_dsl": "GROSS - NET",
                "journal_entries": [],
                "confidence": 0.0
            })

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return "{}"
        except Exception as e:
            return json.dumps({
                "hypothesis": f"Groq API execution error: {str(e)}",
                "discrepancy_type": "API_ERROR",
                "ast_math_dsl": "GROSS - NET",
                "journal_entries": [],
                "confidence": 0.0
            })

    async def stream_reasoning(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield "[Groq API key missing - set GROQ_API_KEY environment variable]"
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": True,
            "temperature": 0.1
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", self.url, headers=headers, json=payload) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and not line.endswith("[DONE]"):
                            try:
                                data = json.loads(line[6:])
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except Exception:
                                pass
        except Exception as e:
            yield f"[Groq Stream Error: {str(e)}]"
