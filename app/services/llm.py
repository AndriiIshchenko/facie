import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

import openai

logger = logging.getLogger(__name__)

# Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()  # "openai" or "mock"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def ask(self, profession, description, question: str) -> str:
        """
        Ask a question about a profession.

        Args:
            profession: The profession name (str or Column)
            description: Optional profession description (str, Column, or None)
            question: The user's question

        Returns:
            Response text from the LLM
        """
        pass

    def _build_prompt(self, profession, description, question: str) -> str:
        """Build a safe, concise prompt."""
        # Convert to string (handle SQLAlchemy Column objects)
        prof_str = str(profession) if profession else "Unknown"
        desc_str = str(description) if description else ""

        context = prof_str
        if desc_str and desc_str.strip():
            context += f" ({desc_str[:100]})"  # Limit description to 100 chars

        prompt = f"""You are a professional advisor. Answer briefly about: {context}

Question: {question}

Keep response under 150 words."""
        return prompt


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing without API keys."""

    async def ask(
        self, profession: str, description: Optional[str], question: str
    ) -> str:
        """Return a mock response."""
        logger.info("Mock LLM: profession=%s, question=%s", profession, question)

        return (
            f"For more functionality purchase Pro plan\n\n"
            f"💼 Profession: {profession}\n"
            f"📝 Question: {question}\n\n"
            f"Note: This is a mock response. To unlock AI-powered insights, "
            f"upgrade to Pro plan with OpenAI integration."
        )


class OpenAILLMProvider(LLMProvider):
    """OpenAI API provider for advanced LLM capabilities."""

    def __init__(self):
        """Initialize OpenAI provider."""
        if not OPENAI_API_KEY:
            logger.warning(
                "OpenAI API key not configured. Falling back to mock responses."
            )
            self.enabled = False
            return

        try:
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
            self.enabled = True
            logger.info("OpenAI provider initialized: model=%s", OPENAI_MODEL)
        except Exception as e:
            logger.warning("Failed to initialize OpenAI: %s", str(e))
            self.enabled = False

    async def ask(
        self, profession: str, description: Optional[str], question: str
    ) -> str:
        """Query OpenAI API for a response."""
        if not self.enabled:
            logger.warning("OpenAI not enabled, returning mock response")
            mock_provider = MockLLMProvider()
            return await mock_provider.ask(profession, description, question)

        try:
            prompt = self._build_prompt(profession, description, question)
            logger.info(
                "OpenAI request: model=%s, profession=%s, question=%s",
                OPENAI_MODEL,
                profession,
                question,
            )

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional advisor. Provide helpful, concise advice.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=200,
            )

            answer = response.choices[0].message.content
            if not answer:
                logger.warning("OpenAI returned empty response")
                mock_provider = MockLLMProvider()
                return await mock_provider.ask(profession, description, question)

            answer = answer.strip()
            logger.info("OpenAI response received: length=%d", len(answer))
            return answer

        except Exception as e:
            logger.error("OpenAI API error: %s", str(e))
            # Fallback to mock on error
            mock_provider = MockLLMProvider()
            return await mock_provider.ask(profession, description, question)


def get_llm_provider() -> LLMProvider:
    """
    Factory function to get the configured LLM provider.

    Returns:
        LLMProvider instance based on LLM_PROVIDER setting
    """
    if LLM_PROVIDER == "openai":
        logger.info("Using OpenAI LLM provider")
        return OpenAILLMProvider()
    else:
        logger.info("Using Mock LLM provider")
        return MockLLMProvider()
