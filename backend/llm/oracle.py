import abc
from typing import List, Optional, Dict
from loguru import logger


class LLMProvider(abc.ABC):
    """Abstract Base Class for LLM Providers"""

    @abc.abstractmethod
    def get_name(self) -> str:
        pass

    @abc.abstractmethod
    async def list_models(self) -> List[str]:
        pass

    @abc.abstractmethod
    async def generate_text(
        self, system_prompt: str, user_prompt: str, model: str
    ) -> str:
        pass


class OpenAIProvider(LLMProvider):
    def get_name(self) -> str:
        return "OpenAI"

    async def list_models(self) -> List[str]:
        # Mock implementation for now
        return ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]

    async def generate_text(
        self, system_prompt: str, user_prompt: str, model: str
    ) -> str:
        logger.info(f"Generating text with OpenAI ({model})...")
        # TODO: Implement actual API call
        return f"[OpenAI {model}] Analysis Result: {user_prompt[:50]}..."


class AnthropicProvider(LLMProvider):
    def get_name(self) -> str:
        return "Anthropic"

    async def list_models(self) -> List[str]:
        return ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"]

    async def generate_text(
        self, system_prompt: str, user_prompt: str, model: str
    ) -> str:
        logger.info(f"Generating text with Anthropic ({model})...")
        return f"[Anthropic {model}] Analysis Result: {user_prompt[:50]}..."


class GoogleProvider(LLMProvider):
    def get_name(self) -> str:
        return "Google"

    async def list_models(self) -> List[str]:
        return ["gemini-1.5-pro", "gemini-1.5-flash"]

    async def generate_text(
        self, system_prompt: str, user_prompt: str, model: str
    ) -> str:
        logger.info(f"Generating text with Google ({model})...")
        return f"[Google {model}] Analysis Result: {user_prompt[:50]}..."


class LLMOracle:
    """
    Provider-Agnostic LLM Oracle Service.
    Manages multiple providers and handles failover/routing.
    """

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "google": GoogleProvider(),
        }
        self.default_provider = "openai"

    async def get_available_models(self) -> Dict[str, List[str]]:
        """
        Returns a dictionary of provider -> [models]
        """
        result = {}
        for name, provider in self.providers.items():
            try:
                models = await provider.list_models()
                result[name] = models
            except Exception as e:
                logger.error(f"Failed to fetch models for {name}: {e}")
                result[name] = []
        return result

    async def analyze(
        self,
        prompt: str,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Main entry point for analysis.
        """
        provider_key = provider_name.lower() if provider_name else self.default_provider
        provider = self.providers.get(provider_key)

        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        # If model is not specified, pick the first one from the list (simplified)
        if not model:
            available = await provider.list_models()
            if available:
                model = available[0]
            else:
                model = "default"

        system_prompt = "You are a highly experienced professional stock trader. Analyze the following market data."

        try:
            return await provider.generate_text(system_prompt, prompt, model)
        except Exception as e:
            logger.error(f"Analysis failed with {provider_key}: {e}")
            return f"Error: {str(e)}"


# Global Oracle Instance
oracle_service = LLMOracle()
