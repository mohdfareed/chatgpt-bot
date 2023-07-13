"""Utilities used by the OpenAI wrapper."""

import asyncio
import json
import logging
import typing

import openai.error
import tenacity

import chatgpt
from chatgpt import core, messages, tools
from chatgpt.openai import tokenization


def _retry(min_wait=1, max_wait=5, max_attempts=6):
    log = tenacity.before_sleep_log(chatgpt.logger, logging.WARNING)
    retry_exceptions = (
        openai.error.Timeout,
        openai.error.APIError,
        openai.error.APIConnectionError,
        openai.error.RateLimitError,
        openai.error.ServiceUnavailableError,
    )

    return tenacity.retry(
        reraise=True,
        stop=tenacity.stop_after_attempt(max_attempts),
        wait=tenacity.wait_random_exponential(min=min_wait, max=max_wait),
        retry=tenacity.retry_if_exception_type(retry_exceptions),
        before_sleep=log,
    )


@_retry()
async def generate_completion(
    **kwargs: typing.Any,
) -> typing.AsyncIterator[dict] | dict | None:
    try:
        completion = await openai.ChatCompletion.acreate(**kwargs)
        if type(completion) == typing.AsyncGenerator:
            return aiter(completion)
        elif type(completion) == dict:
            return completion
        else:
            return None
    except (asyncio.CancelledError, KeyboardInterrupt):
        return None


def create_completion_params(
    config: core.ModelConfig,
    messages: list[messages.Message],
    tools: list[tools.Tool],
) -> dict:
    messages_dict = [m.to_message_dict() for m in messages]
    tools_dict = [t.to_dict() for t in tools]

    # can't send empty list of tools
    if len(tools_dict) < 1:
        tools_dict = None

    # create parameters dict
    parameters = dict(
        messages=messages_dict,
        functions=tools_dict,
        **config.to_dict(),
    )
    # remove None values
    return _clean_params(parameters)  # type: ignore


def parse_completion(
    completion,
    model: core.SupportedChatModel,
) -> messages.ModelMessage:
    choice: dict = completion["choices"][0]
    message: dict = choice.get("message") or choice.get("delta") or {}

    # parse message
    content = message.get("content") or ""
    if function_call := message.get("function_call"):
        reply_dict: dict = json.loads(str(function_call))
        name = reply_dict.get("name") or ""  # default to empty name
        args = reply_dict.get("arguments") or ""  # default to no arguments

        reply = messages.ToolUsage(name, args)
        reply.content = content
    else:  # default to a model message
        reply = messages.ModelMessage(content)

    # load metadata
    reply = _parse_usage(completion, reply, model)
    reply = _parse_finish_reason(completion, reply)
    return reply


def _parse_finish_reason(completion, reply: messages.ModelMessage):
    finish_reason = completion["choices"][0]["finish_reason"]
    if not finish_reason:
        reply.finish_reason = core.FinishReason.UNDEFINED
        return reply
    reply.finish_reason = core.FinishReason(finish_reason)
    return reply


def _parse_usage(
    completion,
    reply: messages.ModelMessage,
    model: core.SupportedChatModel,
):
    try:  # default to 0 if not present
        prompt_tokens = completion["usage"]["prompt_tokens"]
        reply_tokens = completion["usage"]["completion_tokens"]
    except KeyError:
        prompt_tokens = 0
        reply_tokens = 0

    prompt_cost = tokenization.tokens_cost(
        prompt_tokens, model, is_reply=False
    )
    completion_cost = tokenization.tokens_cost(
        reply_tokens, model, is_reply=True
    )
    reply.prompt_tokens = prompt_tokens
    reply.reply_tokens = reply_tokens
    reply.cost = prompt_cost + completion_cost
    return reply


def _clean_params(params):
    if isinstance(params, dict):
        for key, value in list(params.items()):
            if isinstance(value, (list, dict, tuple, set)):
                params[key] = _clean_params(value)
            elif value is None or key is None:
                del params[key]
    elif isinstance(params, (list, set, tuple)):
        params = type(params)(
            _clean_params(item) for item in params if item is not None
        )
    return params
