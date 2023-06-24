"""Core types and classes for ChatGPT."""

import abc
import enum
import json
import typing

import chatgpt.supported_models

T = typing.TypeVar("T", bound="Serializable")


class Serializable(abc.ABC):
    """An object that can be serialized to a JSON dictionary."""

    def __init__(self, **kwargs: typing.Any):
        self.__dict__.update(kwargs)

    def serialize(self):
        """Get the object as a serialized JSON dictionary."""
        json_dict = json.dumps(
            dict(
                serialized_type=type(self).__name__,
                serialized_params=self.__dict__,
            ),
            indent=4,
        )
        return json_dict

    @classmethod
    def deserialize(cls: typing.Type[T], model_json: str) -> T:
        """Deserialize the object from a JSON dictionary of parameters."""
        # deserialize the JSON
        json_dict: dict = json.loads(model_json)
        type_name = json_dict["serialized_type"]
        parameters = json_dict["serialized_params"]
        # get derivative class from serialized type name
        if not (derivative := Serializable._get_subclass(cls, type_name)):
            raise ValueError(
                f"Could not deserialize {type_name} as {cls.__name__}"
            )
        # create instance
        return derivative(**parameters)

    @staticmethod
    def _get_subclass(base_class, subclass_name):
        for subclass in base_class.__subclasses__():
            if subclass.__name__ == subclass_name:
                return subclass
            else:  # recursively check subclasses
                result = Serializable._get_subclass(subclass, subclass_name)
                if result and issubclass(result, base_class):
                    return result
        return None


class ModelConfig(Serializable):
    """ChatGPT model configuration and parameters."""

    def __init__(self, **kwargs: typing.Any) -> None:
        self.model = chatgpt.supported_models.CHATGPT
        """The the model used for chat completions."""
        self.allowed_tool: str | None = None
        """The name of the tool the model must call. Set to an empty string to
        disable tool usage. Defaults to using any tool."""

        self.prompt: SystemMessage | None = None
        """The system prompt of the model. Defaults to a helpful assistant."""
        self.max_tokens: int | None = None
        """The maximum number of tokens to generate. If None, the model will
        not be limited by the number of tokens."""
        self.streaming: bool = False
        """Whether the model streams completions as they are generated."""

        self.temperature: float | None = None
        """Tokens confidence threshold, in range [0.0, 2.0]."""
        self.presence_penalty: float | None = None
        """Penalty for repeated tokens, in range [-2.0, 2.0]."""
        self.frequency_penalty: float | None = None
        """Tokens penalty based on usage frequency, in range [-2.0, 2.0]."""
        super().__init__(**kwargs)

    def to_dict(self) -> dict[str, str | float | list[str] | None]:
        """Convert the model configuration to an OpenAI dictionary."""
        func_call = "none" if self.allowed_tool == "" else self.allowed_tool
        return dict(
            model=self.model.name,
            function_call=func_call,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            stream=self.streaming,
        )


class Message(Serializable, abc.ABC):
    """The base of all messages sent to a model."""

    ROLE: str
    """The role of the message sender."""

    def __init__(
        self, content: str = "", name: str | None = None, **kwargs: typing.Any
    ):
        # content must be a string, even if empty
        if name and not str.isalnum(name.replace("_", "")):  # allow underscore
            raise ValueError("Name must be alphanumeric and 1-64 characters")

        self.content = content
        """The content of the message."""
        self.name = name
        """The name of the message sender."""
        super().__init__(**kwargs)

    def to_message_dict(self):
        """Convert the message to an OpenAI message dictionary."""
        message = dict(
            role=type(self).ROLE,
            content=self.content,
        )
        return message if self.name is None else dict(message, name=self.name)


class UserMessage(Message):
    """A message sent to the model."""

    ROLE = "user"

    def __init__(self, content: str, **kwargs: typing.Any):
        super().__init__(content, **kwargs)


class SystemMessage(Message):
    """A system message sent to the model."""

    ROLE = "system"

    def __init__(self, content: str, **kwargs: typing.Any):
        super().__init__(content, **kwargs)


class ToolResult(Message):
    """The result of a tool usage."""

    ROLE = "function"

    def __init__(self, content: str, name: str, **kwargs: typing.Any):
        super().__init__(content, name, **kwargs)


class ModelMessage(Message):
    """A model generated message."""

    ROLE = "assistant"

    def __init__(self, content, **kwargs: typing.Any):
        self.finish_reason = FinishReason.UNDEFINED
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

    def __init__(
        self, tool_name: str, args_str: str, content="", **kwargs: typing.Any
    ):
        self.args_str = args_str
        """The arguments to the tool usage, as generated by the model."""
        self.tool_name = tool_name
        """The name of the used tool."""
        super().__init__(content, **kwargs)

    @property
    def arguments(self):
        """The arguments to the tool usage."""
        return json.loads(self.args_str)

    def to_message_dict(self):
        return dict(
            super().to_message_dict(),
            function_call=dict(
                name=self.tool_name,
                arguments=self.args_str,
            ),
        )


class SummaryMessage(SystemMessage):
    """A system message containing a summary of the chat history."""

    @property
    def name(self) -> str:
        """Summary message name."""
        return "summary_of_previous_messages"


class FinishReason(enum.StrEnum):
    """The possible reasons for a completion to finish."""

    DONE = "stop"
    """The full completion was generated."""
    TOOL_USE = "function_call"
    """The model is using a tool."""
    LIMIT_REACHED = "length"
    """The token limit or maximum completion tokens was reached."""
    FILTERED = "content_filter"
    """Completion content omitted due to content filter."""
    CANCELLED = "canceled"
    """The completion was canceled by the user."""
    UNDEFINED = "null"
    """The completion is still in progress or incomplete."""


class ModelError(Exception):
    """Exception raised for model errors."""

    pass
