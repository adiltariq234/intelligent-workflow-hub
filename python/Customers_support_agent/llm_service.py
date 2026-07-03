"""LLM service wrapping the Mistral chat model via `langchain-mistralai`.

Provides both a synchronous full-response call and an async streaming
generator, so the API layer can support both SSE/WebSocket streaming and
plain JSON responses from a single service.
"""

import logging
from typing import AsyncIterator, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_mistralai import ChatMistralAI

from app.core.exceptions import LLMError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful, precise AI customer support agent. Answer the "
    "user's question using ONLY the provided context excerpts. If the "
    "context does not contain the answer, say you don't have that "
    "information and suggest the user rephrase or contact a human agent. "
    "Be concise, friendly, and professional. Never invent facts that are "
    "not in the context."
)


class LLMService:
    """Wraps a Mistral chat model for grounded question answering."""

    def __init__(self, api_key: str, model_name: str, temperature: float = 0.2) -> None:
        """Initialize the underlying Mistral chat model.

        Args:
            api_key: Mistral API secret key.
            model_name: Mistral model identifier, e.g. "mistral-large-latest".
            temperature: Sampling temperature; low by default for factual QA.
        """
        self._model = ChatMistralAI(
            api_key=api_key,
            model=model_name,
            temperature=temperature,
            max_retries=2,
        )

    def _build_messages(
        self, question: str, context: str, history_text: str
    ) -> List[SystemMessage | HumanMessage | AIMessage]:
        """Assemble the message list sent to the LLM.

        Args:
            question: The current user question.
            context: Concatenated, cited retrieval context.
            history_text: Prior conversation turns as plain text.

        Returns:
            A list of LangChain message objects.
        """
        user_prompt = (
            f"Conversation so far:\n{history_text or '(none)'}\n\n"
            f"Context excerpts:\n{context or '(no relevant context found)'}\n\n"
            f"Question: {question}"
        )
        return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]

    def generate_answer(self, question: str, context: str, history_text: str) -> str:
        """Generate a full (non-streaming) answer.

        Args:
            question: The current user question.
            context: Concatenated, cited retrieval context.
            history_text: Prior conversation turns as plain text.

        Returns:
            The model's answer text.

        Raises:
            LLMError: If the underlying API call fails.
        """
        try:
            messages = self._build_messages(question, context, history_text)
            response = self._model.invoke(messages)
            return response.content
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM generation failed.")
            raise LLMError(f"Failed to generate a response: {exc}") from exc

    async def stream_answer(
        self, question: str, context: str, history_text: str
    ) -> AsyncIterator[str]:
        """Stream an answer token-by-token (chunk-by-chunk).

        Args:
            question: The current user question.
            context: Concatenated, cited retrieval context.
            history_text: Prior conversation turns as plain text.

        Yields:
            Successive text chunks of the model's answer.

        Raises:
            LLMError: If the underlying streaming call fails.
        """
        try:
            messages = self._build_messages(question, context, history_text)
            async for chunk in self._model.astream(messages):
                if chunk.content:
                    yield chunk.content
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM streaming failed.")
            raise LLMError(f"Failed to stream a response: {exc}") from exc
