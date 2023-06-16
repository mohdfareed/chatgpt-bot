"""Models of the ChatGPT API."""

import typing

from chatgpt import types


class ModelConfig(types.Serializable):
    """ChatGPT model configuration and parameters."""

    def __init__(self) -> None:
        super().__init__()

        self.model: str = str(types.SupportedModel.CHATGPT)
        """The model used for chat completions."""
        self.allowed_tool: str | None = None
        """The name of the tool the model must call. Empty string for no tool.
        Defaults to any tool."""

        self.prompt: str | None = None
        """The system prompt of the model. Defaults to a helpful assistant."""
        self.max_tokens: int | None = None
        """The maximum number of tokens to generate. If None, the model will
        not be limited by the number of tokens."""

        self.temperature: float | None = None
        """Tokens confidence threshold, in range [0.0, 2.0]."""
        self.presence_penalty: float | None = None
        """Penalty for repeated tokens, in range [-2.0, 2.0]."""
        self.frequency_penalty: float | None = None
        """Tokens penalty based on usage frequency, in range [-2.0, 2.0]."""

    def params(self) -> dict[str, str | float | list[str] | None]:
        """Return the model parameters for a generation request."""
        func_call = "none" if self.allowed_tool == "" else self.allowed_tool

        model_params = dict(
            model=self.model,
            function_call=func_call,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
        )
        # remove None values
        return {k: v for k, v in model_params.items() if v is not None}


class UserMessage(types.Message):
    """A message sent to the model."""

    ROLE = "user"


class SystemMessage(types.Message):
    """A system message sent to the model."""

    ROLE = "user"


class ToolResult(types.Message):
    """The result of a tool usage."""

    ROLE = "function"

    @property
    def name(self) -> str:
        """The name of the tool."""
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        super().name = name

    def __init__(self, name: str, content: str) -> None:
        super().__init__(content)
        self._name = name


class ModelReply(types.Reply):
    """A reply to a message in a chat."""

    def __init__(self, content: str) -> None:
        super().__init__()
        self.content = content
        """The content of the reply."""

    def to_message_dict(self) -> dict:
        message = dict(
            role="assistant",
            content=self.content,
        )
        return message


class ToolUsage(types.Reply):
    """A tool use performed by a chat model."""

    def __init__(self, name: str, arguments: dict[str, typing.Any]) -> None:
        super().__init__()
        self.name = name
        """The name of the used tool."""
        self.arguments = arguments
        """The arguments to the tool usage."""

    def to_message_dict(self) -> dict:
        message = dict(
            role="assistant",
            function_call=dict(
                name=self.name,
                arguments=self.arguments,
            ),
        )
        return message
