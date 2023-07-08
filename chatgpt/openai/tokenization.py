"""Tokenization functions of models."""

import tiktoken

import chatgpt.core
import chatgpt.tools


def tokens(string: str, model: chatgpt.core.SupportedChatModel):
    """Get the number of tokens in a string using the model's tokenizer.
    Defaults to 'cl100k_base' if the model does not have a tokenizer.
    """

    try:  # check if a model tokenizer is available
        encoding = tiktoken.encoding_for_model(model.name)
    except:  # the default tokenizer
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))


def messages_tokens(
    messages: list[chatgpt.core.Message],
    model: chatgpt.core.SupportedChatModel,
):
    """Get the number of tokens in a list of messages."""

    num_tokens = 2  # messages are primed with 2 tokens
    for message in messages:
        num_tokens += message_tokens(message, model)
    return num_tokens + 1  # replies are primed with 1 token


def message_tokens(
    message: chatgpt.core.Message,
    model: chatgpt.core.SupportedChatModel,
):
    """Get the number of tokens in a message."""
    count = 0
    if message.content:
        count += tokens(message.content, model) + 3
    if message.name:
        count += tokens(message.name, model) + 2
    else:  # role is omitted if name is present
        count += tokens(message.ROLE(), model)
    if type(message) is chatgpt.core.ToolUsage:
        count += tokens(message.tool_name, model) + 6
        count += tokens(message.args_str, model)
    return count


def tools_tokens(
    tools: list[chatgpt.tools.Tool],
    model: chatgpt.core.SupportedChatModel,
):
    """Get the number of tokens in a list of tools."""
    # FIXME: this is a very rough estimate

    (names, descriptions, parameters) = (0, 0, 0)
    for tool in tools:
        names += tokens(tool.name, model)
        descriptions += tokens(tool.description or "", model)
        for param in tool.parameters:
            parameters += tokens(str(param.to_dict().values()), model)

    num_tokens = 15
    num_tokens += names
    num_tokens += descriptions
    num_tokens += parameters
    return num_tokens


def model_tokens(
    generation: chatgpt.core.ModelMessage,
    model: chatgpt.core.SupportedChatModel,
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
    tokens: int,
    model: chatgpt.core.SupportedChatModel,
    is_reply: bool,
):
    """Get the cost for a number of tokens in USD."""
    cost = model.output_cost if is_reply else model.input_cost
    return float(tokens) / 1000 * cost
