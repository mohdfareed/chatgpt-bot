"""Tokenization functions of models."""

import typing

import tiktoken

import chatgpt.core

if typing.TYPE_CHECKING:
    import chatgpt.tools


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
