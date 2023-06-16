"""Utilities used by ChatGPT."""

import tiktoken

from chatgpt import types


def tokens(string: str, model: str):
    """Get the number of tokens in a string using the model's tokenizer.
    Defaults to 'cl100k_base' if the model does not have a tokenizer.
    """

    try:  # check if a model tokenizer is available
        encoding = tiktoken.encoding_for_model(model)
    except:  # the default tokenizer
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))


def messages_tokens(messages: list[dict], model: types.SupportedModel):
    """Get the number of tokens in a list of messages."""
    # TODO: verify and add tools usage/definition to cost

    if model in types.SupportedModel.gpt3:
        # messages are primed with: <im_start>{role|name}\n{content}<im_end>\n
        tokens_per_message = 4
        # if there's a name, the role is omitted
        tokens_per_name = -1
    elif model in types.SupportedModel.gpt4:
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


def tokens_cost(tokens: int, model: types.SupportedModel, is_reply: bool):
    """Get the cost for a number of tokens in USD."""

    if model is types.SupportedModel.CHATGPT:
        cost = 0.002 if is_reply else 0.0015
    elif model is types.SupportedModel.CHATGPT_16K:
        cost = 0.004 if is_reply else 0.003
    elif model is types.SupportedModel.GPT4:
        cost = 0.06 if is_reply else 0.03
    elif model is types.SupportedModel.GPT4_32K:
        cost = 0.12 if is_reply else 0.06

    return float(tokens) / 1000 * cost
