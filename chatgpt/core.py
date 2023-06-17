"""Models of the ChatGPT API."""

import typing

from chatgpt import types


class ModelConfig(types.Serializable):
    """ChatGPT model configuration and parameters."""

    def __init__(self, **kwargs) -> None:
        self.model_name = types.SupportedModel.CHATGPT
        """The name of the model used for chat completions."""
        self.allowed_tool: str | None = None
        """The name of the tool the model must call. Set to an empty string to
        disable tool usage. Defaults to using any tool."""

        self.prompt: SystemMessage | None = None
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
        super().__init__(**kwargs)

    def params(self) -> dict[str, str | float | list[str] | None]:
        """Return the model parameters for a generation request."""
        func_call = "none" if self.allowed_tool == "" else self.allowed_tool

        model_params = dict(
            model=self.model_name,
            function_call=func_call,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
        )
        # remove None values
        return {k: v for k, v in model_params.items() if v is not None}


class UserMessage(types.ChatMessage):
    """A message sent to the model."""

    ROLE = "user"


class SystemMessage(types.ChatMessage):
    """A system message sent to the model."""

    ROLE = "system"


class ModelMessage(types.ChatMessage):
    """A reply to a message in a chat."""

    ROLE = "assistant"

    def __init__(self, content, **kwargs):
        self.finish_reason = types.FinishReason.UNDEFINED
        """The finish reason of the reply generation."""
        self.prompt_tokens = 0
        """The number of tokens in the prompt provided."""
        self.reply_tokens = 0
        """The number of tokens in the reply generated."""
        self.cost = 0.0
        """The cost of the reply generation, in USD."""
        super().__init__(content, **kwargs)


class ToolUsage(ModelMessage):
    """A tool usage performed by a chat model."""

    def __init__(self, name: str, arguments: dict[str, typing.Any], **kwargs):
        self.tool_name = name
        """The name of the used tool."""
        self.arguments = arguments
        """The arguments to the tool usage."""

        super().__init__("", **kwargs)
        self.content = None

    def to_message_dict(self):
        return dict(
            super().to_message_dict(),
            function_call=dict(
                name=self.tool_name,
                arguments=self.arguments,
            ),
        )


class ToolResult(types.ChatMessage):
    """The result of a tool usage."""

    ROLE = "function"

    @property
    def name(self) -> str:
        """The name of the tool."""
        return self._name

    @name.setter
    def name(self, name: str):
        super().name = name

    def __init__(self, name: str, content: str, **kwargs):
        self._name = name
        super().__init__(content, **kwargs)


class Prompt(types.Serializable):
    """A prompt to be used in a generation request."""

    def __init__(self, template: str, variables: list[str], **kwargs):
        self.template = template
        """The template of the prompt."""
        self.variables = variables
        """The variables in the prompt."""
        super().__init__(**kwargs)

    def load(self, **kwargs: str):
        """Load the prompt with variables."""
        self._validate_args(**kwargs)
        return self.template.format(**kwargs)

    def _validate_args(self, **kwargs):
        """Validate the arguments (variables) the prompt."""
        for arg in kwargs:
            if arg not in self.variables:
                raise ValueError(f"Invalid argument: {arg}")
