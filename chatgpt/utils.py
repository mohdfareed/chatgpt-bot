"""Utilities used by ChatGPT."""

import json
import logging
import typing

import openai.error
import tenacity
import tiktoken

import chatgpt.core
import chatgpt.tools


def retry(min_wait=1, max_wait=60, max_attempts=6):
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


def tokens(string: str, model: chatgpt.core.SupportedModel):
    """Get the number of tokens in a string using the model's tokenizer.
    Defaults to 'cl100k_base' if the model does not have a tokenizer.
    """

    try:  # check if a model tokenizer is available
        encoding = tiktoken.encoding_for_model(model)
    except:  # the default tokenizer
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))


def messages_tokens(
    messages: list[chatgpt.core.Message], model: chatgpt.core.SupportedModel
):
    """Get the number of tokens in a list of messages."""

    num_tokens = 2  # replies are primed with <im_start>assistant
    for message in messages:
        num_tokens += message_tokens(message, model)
    return num_tokens


def message_tokens(
    message: chatgpt.core.Message, model: chatgpt.core.SupportedModel
):
    """Get the number of tokens in a message."""
    # FIXME: test with tools
    if type(message) is chatgpt.core.ToolUsage:
        count = tokens(message.tool_name, model)
        count += tokens(message.args_str, model)
    else:
        count = tokens(message.content, model) + 4
    if message.name:
        count += tokens(message.name, model)
    else:  # role is omitted if name is present
        count += tokens(message.ROLE, model)
    return count


def tools_tokens(
    tools: list[chatgpt.tools.Tool], model: chatgpt.core.SupportedModel
):
    """Get the number of tokens in a list of tools."""
    num_tokens = 0
    for tool in tools:
        num_tokens += tool_tokens(tool, model)
    return num_tokens


def tool_tokens(tool: chatgpt.tools.Tool, model: chatgpt.core.SupportedModel):
    """Get the number of tokens in a tool."""
    count = 0
    # FIXME: implement tool tokens
    return count


def model_tokens(
    generation: chatgpt.core.ModelMessage,
    model: chatgpt.core.SupportedModel,
    has_tools=False,
):
    """Get the number of tokens in a model generation results."""
    count = 0 if has_tools else -1
    if generation.content:
        count += tokens(generation.content, model)
        count += 1
    if type(generation) == chatgpt.core.ToolUsage:
        count += tokens(generation.tool_name, model)
        count += tokens(generation.args_str, model)
        count += 4
    return count


def tokens_cost(
    tokens: int, model: chatgpt.core.SupportedModel, is_reply: bool
):
    """Get the cost for a number of tokens in USD."""

    # read https://openai.com/pricing/ for more information
    if model is chatgpt.core.SupportedModel.CHATGPT:
        cost = 0.002 if is_reply else 0.0015
    elif model is chatgpt.core.SupportedModel.CHATGPT_16K:
        cost = 0.004 if is_reply else 0.003
    elif model is chatgpt.core.SupportedModel.GPT4:
        cost = 0.06 if is_reply else 0.03
    elif model is chatgpt.core.SupportedModel.GPT4_32K:
        cost = 0.12 if is_reply else 0.06

    return float(tokens) / 1000 * cost


@retry()
async def completion(
    **kwargs: typing.Any,
) -> typing.AsyncIterator[dict] | dict:
    """Use tenacity to retry the async completion call."""
    return await openai.ChatCompletion.acreate(**kwargs)  # type: ignore


def parse_completion(
    completion: dict,
    model: chatgpt.core.SupportedModel,
) -> chatgpt.core.ModelMessage:
    """Parse a completion response from the OpenAI API. Returns the appropriate
    model message. Required fields are set to default values if not present."""
    choice: dict = completion["choices"][0]
    message: dict = choice.get("message") or choice.get("delta") or {}

    # parse message
    content = message.get("content") or ""
    if function_call := message.get("function_call"):
        reply_dict: dict = json.loads(str(function_call))
        name = reply_dict.get("name") or ""  # default to empty name
        args = reply_dict.get("arguments") or "{}"  # default to empty dict

        reply = chatgpt.core.ToolUsage(name, args)
        reply.content = content
    else:  # default to a model message
        reply = chatgpt.core.ModelMessage(content)

    # load metadata
    reply = _parse_usage(completion, reply, model)
    reply = _parse_finish_reason(completion, reply)
    return reply


def _parse_finish_reason(completion, reply: chatgpt.core.ModelMessage):
    finish_reason = completion["choices"][0]["finish_reason"]
    if not finish_reason:
        reply.finish_reason = chatgpt.core.FinishReason.UNDEFINED
        return reply
    reply.finish_reason = chatgpt.core.FinishReason(finish_reason)
    return reply


def _parse_usage(completion, reply: chatgpt.core.ModelMessage, model):
    try:  # default to 0 if not present
        prompt_tokens = completion["usage"]["prompt_tokens"]
        reply_tokens = completion["usage"]["completion_tokens"]
    except KeyError:
        prompt_tokens = 0
        reply_tokens = 0

    prompt_cost = tokens_cost(prompt_tokens, model, is_reply=False)
    completion_cost = tokens_cost(reply_tokens, model, is_reply=True)
    reply.cost = prompt_cost + completion_cost
    reply.prompt_tokens = prompt_tokens
    reply.reply_tokens = reply_tokens
    return reply
