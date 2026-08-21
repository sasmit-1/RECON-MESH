"""
RECON-MESH Local Ollama Provider (Step 07)
Provides 0-egress local edge LLM inference via Ollama REST API.
"""

import json
from typing import AsyncGenerator
import httpx

from backend.app.agent.base_provider import BaseLLMEngine


class LocalOllamaLLM(BaseLLMEngine):
    """
    Local Ollama LLM provider executing 100% air-gapped on edge hardware.
    Targets Ollama REST API (/api/generate).
    """

    def __init__(self, endpoint: str = "http://127.0.0.1:11434", model: str = "qwen2:1.5b-instruct-q4_K_M"):
        self.endpoint = endpoint.rstrip("/")
        self.model = model

    async def generate_resolution(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_ctx": 4096}
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except Exception as e:
            return json.dumps({
                "hypothesis": f"Local Ollama inference offline fallback: {str(e)}",
                "discrepancy_type": "SYSTEM_OFFLINE",
                "ast_math_dsl": "GROSS - NET",
                "journal_entries": [],
                "confidence": 0.0
            })

    async def stream_reasoning(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": True,
            "options": {"temperature": 0.1, "num_ctx": 4096}
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                token = data.get("response", "")
                                if token:
                                    yield token
                            except Exception:
                                pass
        except Exception as e:
            yield f"[Ollama Connection Warning: {str(e)}]"
