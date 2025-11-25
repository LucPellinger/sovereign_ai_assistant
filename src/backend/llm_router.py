# backend/llm_router.py
import os
from typing import Optional
from langchain_openai import ChatOpenAI

class LLMRouter:
    def __init__(self):
        '''Initialize LLM Router with local and remote model configurations.
        '''
        # Local (Ollama)
        self.local_model = os.getenv("LOCAL_MODEL_NAME", "llama3.2:latest")
        self.local_base  = os.getenv("LOCAL_BASE_URL", "http://ollama:11434/v1")

        # Remote (OpenRouter)
        self.remote_model = os.getenv("REMOTE_MODEL_NAME", "qwen/qwen3-30b-a3b:free")
        self.remote_base  = os.getenv("REMOTE_BASE_URL", "https://openrouter.ai/api/v1")
        self.remote_key   = os.getenv("OPENROUTER_API_KEY", "")

        self._local_llm  = ChatOpenAI(model=self.local_model,  api_key="ollama", base_url=self.local_base)
        self._remote_llm = ChatOpenAI(model=self.remote_model, api_key=self.remote_key, base_url=self.remote_base) if self.remote_key else None

    def pick(self, mode: str = "local", model_override: Optional[str] = None) -> ChatOpenAI:
        '''Pick an LLM based on mode and optional model override.

        Args:
            mode: "local", "remote", or "auto" to select LLM.
            model_override: Specific model name to override default.
        Returns:
            An instance of ChatOpenAI configured for the selected model.
        '''
        m = (mode or "local").lower()
        if m == "local":
            if model_override and model_override != self.local_model:
                return ChatOpenAI(model=model_override, api_key="ollama", base_url=self.local_base)
            return self._local_llm

        if m == "remote":
            if not self._remote_llm:
                raise RuntimeError("Remote LLM not configured (missing OPENROUTER_API_KEY).")
            if model_override and model_override != self.remote_model:
                return ChatOpenAI(model=model_override, api_key=self.remote_key, base_url=self.remote_base)
            return self._remote_llm

        # auto: prefer remote if configured
        if self._remote_llm:
            return self._remote_llm
        return self._local_llm
