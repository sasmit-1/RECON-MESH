"""
RECON-MESH Gemini Provider (Step 07)
Provides cloud-based Gemini LLM inference for quick evaluation.
"""

import json
from typing import AsyncGenerator
import httpx

from backend.app.agent.base_provider import BaseLLMEngine


class GeminiLLM(BaseLLMEngine):
    """
    Gemini REST client provider.
    """

    def __init__(self, api_key: str = "", model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}"

    async def generate_resolution(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            return json.dumps({
                "hypothesis": "Gemini API key not configured (GEMINI_API_KEY missing).",
                "discrepancy_type": "UNCONFIGURED_API_KEY",
                "ast_math_dsl": "GROSS - NET",
                "journal_entries": [],
                "confidence": 0.0
            })

        url = f"{self.base_url}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                return "{}"
        except Exception as e:
            return json.dumps({
                "hypothesis": f"Gemini API execution error: {str(e)}",
                "discrepancy_type": "API_ERROR",
                "ast_math_dsl": "GROSS - NET",
                "journal_entries": [],
                "confidence": 0.0
            })

    async def stream_reasoning(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield "[Gemini API key missing - set GEMINI_API_KEY environment variable]"
            return

        url = f"{self.base_url}:streamGenerateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                candidates = data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    if parts:
                                        yield parts[0].get("text", "")
                            except Exception:
                                pass
        except Exception as e:
            yield f"[Gemini Stream Error: {str(e)}]"
