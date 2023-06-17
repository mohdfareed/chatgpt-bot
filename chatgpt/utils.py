"""Utilities used by ChatGPT."""

import json
import logging
import typing

import openai.error
import tenacity
import tiktoken

import chatgpt.core


class ClassPropertyDescriptor(object):
    # read more at https://stackoverflow.com/questions/5189699/how-to-make-a-class-property
    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, cls=None):
        if cls is None:
            cls = type(obj)
        return self.fget.__get__(obj, cls)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self


def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


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


@retry()
async def completion(
    **kwargs: typing.Any,
) -> typing.AsyncIterator[dict] | dict:
    """Use tenacity to retry the async completion call."""
    return await openai.ChatCompletion.acreate(**kwargs)  # type: ignore


def parse_completion(
    completion: dict,
    model: chatgpt.core.SupportedModel,
) -> chatgpt.core.ModelMessage | chatgpt.core.ToolUsage:
    """Parse a completion response from the OpenAI API."""

    # parse metadata
    finish_reason = chatgpt.core.FinishReason(
        completion["choices"][0]["finish_reason"]
    )
    prompt_tokens = completion["usage"]["prompt_tokens"]
    prompt_cost = tokens_cost(prompt_tokens, model, is_reply=False)
    reply_tokens = completion["usage"]["completion_tokens"]
    completion_cost = tokens_cost(reply_tokens, model, is_reply=True)

    # parse reply
    message = completion["choices"][0]["message"]
    if content := message.get("content"):
        reply = chatgpt.core.ModelMessage(content)
    elif function_call := message.get("function_call"):
        reply_json = json.loads(str(function_call))
        name = reply_json.pop("name")
        args = reply_json.pop("arguments")
        reply = chatgpt.core.ToolUsage(name, args)
    else:
        raise ValueError("Invalid completion message received")

    # load metadata
    reply.cost = prompt_cost + completion_cost
    reply.prompt_tokens = prompt_tokens
    reply.reply_tokens = reply_tokens
    reply.finish_reason = finish_reason
    return reply
