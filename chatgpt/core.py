"""Classes and functions used by different components of the package.
"""

from contextlib import contextmanager
from typing import Any, Coroutine, Dict, Generator, List
from uuid import UUID

import tiktoken
from langchain.callbacks import OpenAICallbackHandler, manager
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import BaseMessage, HumanMessage, LLMResult


class StreamHandler(AsyncCallbackHandler):
    """Async callback handler for streaming generation."""

    def __init__(self, gen):
        super().__init__()
        self._handle_token = gen

    async def on_llm(self, *_, **__):
        # needed to avoid 'langchain.callbacks.manager' warning
        pass

    async def on_llm_new_token(self, token: str, **kwargs):
        await self._handle_token(token)

    async def on_llm_end(self, response: LLMResult, **kwargs):
        await self._handle_token(None)  # signal end of generation


class MetricsHandler(OpenAICallbackHandler, AsyncCallbackHandler):
    """OpenAI callback handler for request metrics."""

    def __init__(self) -> None:
        super().__init__()

    async def on_llm(self, *args, **kwargs):
        # needed to avoid 'langchain.callbacks.manager' warning
        pass

    async def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        self.input_messages = prompts
        return super().on_llm_start(serialized, prompts, **kwargs)

    async def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Coroutine[Any, Any, Any]:
        # flatten messages
        self.input_messages = [m for l in messages for m in l]
        return await super().on_chat_model_start(
            serialized,
            messages,
            run_id=run_id,
            parent_run_id=parent_run_id,
            **kwargs,
        )

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        # manually calculate usage if streaming
        if response.llm_output and not response.llm_output.get("token_usage"):
            model = response.llm_output["model_name"]
            prompt_tokens = 0
            completion_tokens = 0

            # calculate tokens for all generations
            for output in response.generations:
                for generation in output:
                    completion_tokens = token_count(model, generation.text)
                    prompt_tokens = messages_token_count(
                        model, self.input_messages
                    )

            # set usage
            token_usage = dict()
            token_usage["prompt_tokens"] = prompt_tokens
            token_usage["completion_tokens"] = completion_tokens
            token_usage["total_tokens"] = prompt_tokens + completion_tokens

            response.llm_output["token_usage"] = token_usage

        super().on_llm_end(response, **kwargs)

    @classmethod
    @contextmanager
    def callback(cls) -> Generator["MetricsHandler", None, None]:
        """Get OpenAI callback handler in a context manager."""
        callback = MetricsHandler()
        manager.openai_callback_var.set(callback)
        yield callback
        manager.openai_callback_var.set(None)


class GenerationResults:
    text: str
    """The generated text."""
    prompt_tokens: int
    """The number of tokens in the prompt."""
    generated_tokens: int
    """The number of tokens in the generated text."""
    request_count: int
    """The number of successful requests made to models."""
    cost: float
    """The cost of the generation request, in USD."""

    def __init__(self, result: str, callback: OpenAICallbackHandler):
        self.text = result
        self.prompt_tokens = callback.prompt_tokens
        self.generated_tokens = callback.completion_tokens
        self.request_count = callback.successful_requests
        self.cost = callback.total_cost


def token_count(model: str, string: str) -> int:
    """Get the number of tokens in a string using the model's tokenizer. If
    the model does not have a tokenizer, 'cl100k_base' is used.

    Args:
        text (str): The text to tokenize.

    Returns:
        int: The number of tokens in the text.
    """

    try:  # check if a model tokenizer is available
        encoding = tiktoken.encoding_for_model(model)
    except:  # the default tokenizer
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))


def messages_token_count(
    model_name: str,
    messages: list[BaseMessage] | list[str],
) -> int:
    """Get the number of tokens in a list of messages. Strings are converted to
    HumanMessages. A name can be provided as an additional keyword argument to
    the message's constructor.

    Args:
        model_name (str): The name of the model to use for tokenization.
        messages (list[BaseMessage | str]): The messages to tokenize.

    Returns:
        int: The number of tokens in the messages when sent as a prompt.
    """

    # convert non-BaseMessage messages to HumanMessage
    _messages: list[BaseMessage] = []
    for message in messages:
        if not isinstance(message, BaseMessage):
            _messages.append(HumanMessage(content=str(message)))
            continue
        _messages.append(message)

    # convert messages to dictionaries
    messages_dict = []
    roles = dict(system="system", ai="assistant", human="user")
    for message in _messages:
        message_dict = dict(
            role=roles[message.type],
            content=message.content,
        )
        # add name if available in additional_kwargs
        if name := message.additional_kwargs.get("name"):
            message_dict["name"] = name
        messages_dict.append(message_dict)

    return _prompt_tokens_count(model_name, messages_dict)


def _prompt_tokens_count(model: str, messages: list[dict[str, str]]) -> int:
    # NOTE: the number of tokens per message/name are model dependent. Check
    # [docs](https://platform.openai.com/docs/guides/chat/managing-tokens)
    # for more information.

    tokens_per_message = 4  # every message has 4 tokens encoding
    tokens_per_name = -1  # name replaces role

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():  # role, name, and content
            num_tokens += tokens_per_name if key == "name" else 0
            num_tokens += token_count(model, value)  # role/name and content

    num_tokens += 3  # every response is primed with 3 tokens
    return num_tokens
