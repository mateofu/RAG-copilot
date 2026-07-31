from dataclasses import dataclass
from typing import Protocol


class ChatProviderError(Exception):
    code = "chat_provider_failed"


class InvalidChatCitationsError(ChatProviderError):
    code = "invalid_chat_citations"


@dataclass(frozen=True, slots=True)
class ChatResult:
    content: str
    input_tokens: int
    output_tokens: int


class ChatProvider(Protocol):
    async def answer(self, system_prompt: str, user_prompt: str) -> ChatResult: ...
