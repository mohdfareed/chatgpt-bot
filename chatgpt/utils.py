"""Utilities used by ChatGPT."""

import logging

import openai.error
import tenacity
import tiktoken

import chatgpt


def tokens(string: str, model: str):
    """Get the number of tokens in a string using the model's tokenizer.
    Defaults to 'cl100k_base' if the model does not have a tokenizer.
    """

    try:  # check if a model tokenizer is available
        encoding = tiktoken.encoding_for_model(model)
    except:  # the default tokenizer
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))


def messages_tokens(messages: list[dict], model: chatgpt.types.SupportedModel):
    """Get the number of tokens in a list of messages."""
    # TODO: verify and add tools usage/definition to cost

    if model in chatgpt.types.SupportedModel.gpt3_models():
        # messages are primed with: <im_start>{role|name}\n{content}<im_end>\n
        tokens_per_message = 4
        # if there's a name, the role is omitted
        tokens_per_name = -1
    elif model in chatgpt.types.SupportedModel.gpt4_models():
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
    tokens: int, model: chatgpt.types.SupportedModel, is_reply: bool
):
    """Get the cost for a number of tokens in USD."""

    if model is chatgpt.types.SupportedModel.CHATGPT:
        cost = 0.002 if is_reply else 0.0015
    elif model is chatgpt.types.SupportedModel.CHATGPT_16K:
        cost = 0.004 if is_reply else 0.003
    elif model is chatgpt.types.SupportedModel.GPT4:
        cost = 0.06 if is_reply else 0.03
    elif model is chatgpt.types.SupportedModel.GPT4_32K:
        cost = 0.12 if is_reply else 0.06

    return float(tokens) / 1000 * cost


def retry_decorator(min_wait=1, max_wait=60, max_attempts=6):
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
