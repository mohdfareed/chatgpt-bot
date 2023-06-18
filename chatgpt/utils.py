"""Utilities used by ChatGPT."""

import json
import logging
import typing

import openai.error
import tenacity
import tiktoken

import chatgpt.core


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


def tokens(string: str, model: str):
    """Get the number of tokens in a string using the model's tokenizer.
    Defaults to 'cl100k_base' if the model does not have a tokenizer.
    """

    try:  # check if a model tokenizer is available
        encoding = tiktoken.encoding_for_model(model)
    except:  # the default tokenizer
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))


def messages_tokens(messages: list[dict], model: chatgpt.core.SupportedModel):
    """Get the number of tokens in a list of messages."""
    # TODO: verify and add tools usage/definition to cost

    if model in chatgpt.core.SupportedModel.gpt3_models():
        # messages are primed with: <im_start>{role|name}\n{content}<im_end>\n
        tokens_per_message = 4
        # if there's a name, the role is omitted
        tokens_per_name = -1
    elif model in chatgpt.core.SupportedModel.gpt4_models():
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise NotImplementedError(f"Model '{model}' is not supported")

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += tokens(value, str(model))
            if key == "name":
                num_tokens += tokens_per_name
    # replies are primed with <im_start>assistant
    num_tokens += 2
    return num_tokens


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

    # parse text
    choice = completion["choices"][0]
    message = choice.get("message") or choice.get("delta")

    if content := message.get("content"):
        reply = chatgpt.core.ModelReply(content)
    elif function_call := message.get("function_call"):
        reply_dict: dict = json.loads(str(function_call))
        name = reply_dict.get("name") or ""  # default to empty name
        args = reply_dict.get("arguments")
        reply = chatgpt.core.ToolUsage(name, args)
    else:  # default to empty message
        reply = chatgpt.core.ModelMessage("")

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
