"""Utilities used by ChatGPT."""

import tiktoken

from chatgpt import types


def tokens(string: str, model: str) -> int:
    """Get the number of tokens in a string using the model's tokenizer.
    Defaults to 'cl100k_base' if the model does not have a tokenizer.

    Args:
        string (str): The string to count tokens in.
        model (str): The model to use for tokenization.

    Returns:
        int: The number of tokens in the string.
    """

    try:  # check if a model tokenizer is available
        encoding = tiktoken.encoding_for_model(model)
    except:  # the default tokenizer
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))


def messages_tokens(messages: list[dict], model: types.ChatModel) -> int:
    """Get the number of tokens in a list of messages (a prompt).

    Args:
        messages (list[dict]): A list of messages forming a prompt. Each
        message is a dictionary of role, name, and content.
        model (GPTModel): The model to use for tokenization.

    Returns:
        int: The number of tokens in the list of messages.
    """

    if model in (types.ChatModel.CHATGPT, types.ChatModel.CHATGPT_16K):
        # every message is primed with:
        # <im_start>{role/name}\n{content}<im_end>\n
        tokens_per_message = 4
        # if there's a name, the role is omitted
        tokens_per_name = -1
    elif model in (types.ChatModel.GPT4, types.ChatModel.GPT4_32K):
        # TODO: check if correct
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
    # every reply is primed with <im_start>assistant
    num_tokens += 2
    return num_tokens
