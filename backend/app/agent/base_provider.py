"""
RECON-MESH Base LLM Provider & Dynamic Factory (Step 07)
Defines the abstract interface for pluggable LLM inference engines and the
factory router supporting local Ollama edge nodes, Gemini, and Groq cloud providers.
"""

from abc import ABC, abstractmethod
import os
from typing import AsyncGenerator, Dict, Any, Optional


class BaseLLMEngine(ABC):
    """
    Abstract interface decoupling LLM inference from core reconciliation business logic.
    Supports both full-response generation and token-by-token streaming.
    """

    @abstractmethod
    async def generate_resolution(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generates full text / JSON response from the LLM.
        """
        pass

    @abstractmethod
    async def stream_reasoning(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        """
        Streams token-by-token reasoning for live UI terminal playback.
        """
        pass


def get_llm_engine() -> BaseLLMEngine:
    """
    Factory function resolving active LLM engine based on environment configuration.
    
    Order of preference:
    1. USE_EDGE_INFERENCE=true or LLM_PROVIDER=local_ollama -> LocalOllamaLLM
    2. LLM_PROVIDER=groq -> GroqLLM
    3. Default/LLM_PROVIDER=gemini -> GeminiLLM
    """
    use_edge = os.getenv("USE_EDGE_INFERENCE", "false").strip().lower() == "true"
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()

    if use_edge or provider in ("local_ollama", "ollama", "edge"):
        from backend.app.agent.local_llm import LocalOllamaLLM
        endpoint = os.getenv("EDGE_NODE_URL", "http://127.0.0.1:11434")
        model = os.getenv("EDGE_MODEL_NAME", "qwen2:1.5b-instruct-q4_K_M")
        return LocalOllamaLLM(endpoint=endpoint, model=model)

    elif provider == "groq":
        from backend.app.agent.groq_client import GroqLLM
        api_key = os.getenv("GROQ_API_KEY", "")
        model = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
        return GroqLLM(api_key=api_key, model=model)

    else:
        from backend.app.agent.gemini_client import GeminiLLM
        api_key = os.getenv("GEMINI_API_KEY", "")
        model = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
        return GeminiLLM(api_key=api_key, model=model)
