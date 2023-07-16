"""Tokenization functions of models."""

import tiktoken

from chatgpt import core, logger, messages, tools


def tokens(string: str, model: core.SupportedChatModel):
    """Get the number of tokens in a string using the model's tokenizer.
    Defaults to 'cl100k_base' if the model does not have a tokenizer.
    """

    try:  # check if a model tokenizer is available
        encoding = tiktoken.encoding_for_model(model.name)
    except:  # the default tokenizer
        logger.warning(f"Tokenizer not found for model: {model.name}")
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))


def messages_tokens(
    messages: list[messages.Message], model: core.SupportedChatModel
):
    """Get the number of tokens in a list of messages."""

    num_tokens = 2  # messages are primed with 2 tokens
    for message in messages:
        num_tokens += message_tokens(message, model)

    num_tokens += 16  # for tool usage
    return num_tokens + 1  # replies are primed with 1 token


def message_tokens(message: messages.Message, model: core.SupportedChatModel):
    """Get the number of tokens in a message."""
    count = 0
    if message.content:
        count += tokens(message.content, model) + 3

    if message.name:
        count += tokens(message.name, model) + 2
    else:  # role is omitted if name is present
        count += tokens(message.ROLE(), model)

    if type(message) is messages.ToolUsage:
        count += tokens(message.tool_name, model) + 6
        count += tokens(message.args_str, model)
    return count


def tools_tokens(tools: list[tools.Tool], model: core.SupportedChatModel):
    """Return the number of tokens used by a list of functions."""
    # FIXME: this is a very rough estimate

    num_tokens = 0
    for tool in tools:
        function_tokens = tokens(tool.name, model)
        function_tokens += tokens(tool.description, model)
        if tool.parameters:
            for param in tool.parameters:
                function_tokens += tokens(param.name, model)
                if param.type:
                    function_tokens += 2
                    function_tokens += tokens(param.type, model)
                if param.description:
                    function_tokens += 2
                    function_tokens += tokens(param.description, model)
                if param.enum:
                    function_tokens -= 3
                    for v in param.enum:
                        function_tokens += 3
                        function_tokens += tokens(v, model)
            function_tokens += 11
        num_tokens += function_tokens
    num_tokens += 12
    return num_tokens


def model_tokens(
    generation: messages.ModelMessage,
    model: core.SupportedChatModel,
    has_tools=False,
):
    """Get the number of tokens in a model generation results."""
    count = 0 if has_tools else -1
    if generation.content:
        count += tokens(generation.content, model)
        count += 1
    if type(generation) == messages.ToolUsage:
        count += tokens(generation.tool_name, model)
        count += tokens(generation.args_str, model)
        count += 4
    return count


def tokens_cost(tokens: int, model: core.SupportedChatModel, is_reply: bool):
    """Get the cost for a number of tokens in USD."""
    cost = model.output_cost if is_reply else model.input_cost
    return float(tokens) / 1000 * cost
