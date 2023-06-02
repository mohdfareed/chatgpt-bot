"""ChatGPT interface that sends prompts and receives replies.
"""

import asyncio
from datetime import datetime
from typing import AsyncGenerator

import openai
import openai.error as openai_error
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from chatgpt import logger
from chatgpt.errors import *
from chatgpt.model import ChatGPT
from chatgpt.types import *


class ChatCompletion:
    """Chat completions generator for sending and receiving messages from
    OpenAI."""

    def __init__(self, model: ChatGPT):
        """Create a ChatCompletion instance."""

        self.model = model

    def generate(self, chat: GPTChat, max_tokens=0) -> GPTReply:
        """Send a prompt to the chat and generate a response.

        Args:
            chat (ChatHistory): Chat messages for which to generate a response.
            max_tokens (int): Positive integer of the maximum number of tokens
            to generate. Defaults to no limit (0).

        Returns:
            Reply: The generated reply.

        Raises:
            CompletionError: If requesting the completion fails.
            ConnectionError: If the request fails due to connectivity.
            TokenLimitError: If the prompt and completion tokens exceed the
            maximum allowed tokens.
        """

        if max_tokens is int and int(str(max_tokens)) < 1:
            raise ValueError("Max tokens must be a positive integer.")

        completion: dict
        logger.debug(f"requesting completion...")
        completion = _request_completion(self.model, chat, max_tokens)
        logger.debug(f"completion received")

        # parse completion
        reply = GPTReply("", FinishReason.UNDEFINED.value)
        reply += str(completion["choices"][0]["message"]["content"])
        reply.created = datetime.fromtimestamp(completion["created"])
        reply.finish_reason = FinishReason(
            completion["choices"][0]["finish_reason"]
        )

        # calculate response tokens cost
        reply.prompt_tokens = self.model.prompt_tokens(chat)
        reply.reply_tokens = self.model.tokens(str(reply))
        # check for usage mismatch
        if reply.prompt_tokens != completion["usage"]["prompt_tokens"]:
            logger.warning("completion tokens usage mismatched")
        return reply

    async def stream(
        self, chat: GPTChat, max_tokens=0
    ) -> AsyncGenerator[GPTReply, None]:
        """Send a prompt to OpenAI and receive a generator of the response.

        Args:
            chat (list): Messages history for which to generate a response.
            max_tokens (int): Positive integer of the maximum number of tokens
            to generate. Defaults to no limit (0).

        Returns:
            AsyncGenerator: An asynchronous generator that yields Reply objects
            with the most up-to-date response.

        Raises:
            CompletionError: If requesting the completion fails.
            ConnectionError: If the stream fails due to connectivity.
            TokenLimitError: If the prompt and completion tokens exceed the
            maximum allowed tokens.
        """

        if max_tokens is int and int(str(max_tokens)) < 1:
            raise ValueError("Max tokens must be a positive integer.")

        logger.debug(f"requesting asynchronous completion...")
        completion = await _async_completion(self.model, chat, max_tokens)
        logger.debug(f"asynchronous completion received")

        # start a task to parse the completion packets
        logger.debug("request in progress...")
        reply: GPTReply = GPTReply("", FinishReason.UNDEFINED.value)
        async for packet in _parse_completion(completion):
            reply.data += packet[0]
            reply.finish_reason = packet[1]
            reply.created = packet[2]
            reply.prompt_tokens = self.model.prompt_tokens(chat)
            reply.reply_tokens = self.model.tokens(str(reply))
            yield reply
        logger.debug("request completed")


@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(6),
    retry=retry_if_exception_type(ConnectionError),
    reraise=True,
)
async def _parse_completion(completion) -> AsyncGenerator:
    finish_reason: FinishReason = FinishReason.UNDEFINED

    try:  # parse and handle completion packets
        async for packet in completion:
            # parse completion metadata
            creation_time = datetime.fromtimestamp(packet["created"])
            if fr := packet["choices"][0]["finish_reason"]:
                finish_reason = FinishReason(fr)

            # parse completion text if available
            if "content" in (text := packet["choices"][0]["delta"]):
                content = str(text["content"])
                yield content, finish_reason, creation_time

            await asyncio.sleep(0)
    except Exception as e:
        raise _handle_exception(e)
    finally:  # close the completion stream when done
        await completion.aclose()


@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(6),
    retry=retry_if_exception_type(ConnectionError),
    reraise=True,
)
def _request_completion(model: ChatGPT, chat: GPTChat, tokens) -> dict:
    try:  # request completion packets
        completion = openai.ChatCompletion.create(
            **model.params(),
            messages=chat.to_dict(),
            max_tokens=tokens if tokens > 0 else None,
        )
    except Exception as e:
        raise _handle_exception(e)
    return dict(iter(completion))


@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(6),
    retry=retry_if_exception_type(ConnectionError),
    reraise=True,
)
async def _async_completion(model: ChatGPT, chat: GPTChat, tokens):
    try:  # request completion packets
        completion = await openai.ChatCompletion.acreate(
            **model.params(),
            messages=chat.to_dict(),
            max_tokens=tokens if tokens > 0 else None,
            stream=True,
        )
    except Exception as e:
        raise _handle_exception(e)
    return completion  # type: ignore


def _handle_exception(e: Exception) -> Exception:
    connection_errors = (
        openai_error.APIConnectionError,
        openai_error.APIError,
        openai_error.Timeout,
        openai_error.RateLimitError,
        openai_error.ServiceUnavailableError,
    )
    if e is openai_error.InvalidRequestError:
        if "This model's maximum context length is" in str(e):
            logger.warning(f"context limit error: {e}")
            return TokenLimitError()
        return CompletionError(f"Invalid request: {e}")
    if e is openai_error.AuthenticationError:
        return CompletionError(f"Authentication error: {e}")
    if e in connection_errors:
        logger.debug(f"connection error: {e}")
        return ConnectionError()

    logger.error(f"unknown error: {e}")
    return e
