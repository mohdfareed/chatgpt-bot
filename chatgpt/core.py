"""Core types and classes for ChatGPT."""

import abc
import enum
import json
import textwrap
import typing
import uuid

T = typing.TypeVar("T", bound="Serializable")


class ModelError(Exception):
    """Exception raised for model errors."""

    pass


class Serializable(abc.ABC):
    """An object that can be serialized to a JSON dictionary string."""

    def __init__(self, **kwargs: typing.Any):
        self.__dict__.update(kwargs)

    def serialize(self) -> str:
        """Get the object as a serialized string."""
        serialized_dict = {
            # store the type's fully-qualified name to allow deserialization
            "serialized_type": type(self).__qualname__,
            # recursively serialize all serializable attributes
            "serialized_params": {
                key: value.serialize()
                if isinstance(value, Serializable)
                else value
                for key, value in self.__dict__.items()
            },
        }
        return json.dumps(serialized_dict)

    @classmethod
    def deserialize(cls: typing.Type[T], serialized_string: str) -> T:
        """Deserialize the object from a string of parameters."""
        serialized_dict = json.loads(serialized_string)
        serialized_type = serialized_dict["serialized_type"]
        parameters = serialized_dict["serialized_params"]

        # get derivative class from serialized type name
        derivative = Serializable._get_subclass(Serializable, serialized_type)
        if derivative is None:
            raise ValueError(
                f"Could not deserialize {serialized_type} as {cls.__name__}"
            )

        # handle nested serialized objects
        for key, value in parameters.items():
            if isinstance(value, str):
                try:  # check if value is a serialized object string
                    potential_object_dict = json.loads(value)
                    if (
                        isinstance(potential_object_dict, dict)
                        and "serialized_type" in potential_object_dict
                    ):
                        parameters[key] = Serializable.deserialize(value)
                except json.JSONDecodeError:
                    pass  # value is not a serialized object string

        # create instance
        return derivative(**parameters)

    @staticmethod
    def _get_subclass(
        base_class: typing.Type, subclass_name: str
    ) -> typing.Type:
        subclasses: list[typing.Type] = base_class.__subclasses__()
        for subclass in subclasses:
            if subclass.__qualname__ == subclass_name:
                return subclass
            else:
                sub_subclass = Serializable._get_subclass(
                    subclass, subclass_name
                )
                if sub_subclass is not None:
                    return sub_subclass
        return None


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


class SupportedChatModel(Serializable):
    """A supported GPT model."""

    def __init__(
        self,
        name="",
        size=0,
        input_cost=0.0,
        output_cost=0.0,
        **kwargs: typing.Any,
    ):
        self._name = name
        self._size = size
        self._input_cost = input_cost
        self._output_cost = output_cost
        super().__init__(**kwargs)

    @property
    def name(cls) -> str:
        """The name of the model."""
        return cls._name

    @property
    def size(cls) -> int:
        """The size of input the model can accept in tokens."""
        return cls._size

    @property
    def input_cost(cls) -> float:
        """The cost of input tokens, in USD and per 1k tokens."""
        return cls._input_cost

    @property
    def output_cost(cls) -> float:
        """The cost of output tokens, in USD and per 1k tokens."""
        return cls._output_cost


class ModelConfig(Serializable):
    """ChatGPT model configuration and parameters."""

    def __init__(self, **kwargs: typing.Any) -> None:
        self.model = CHATGPT
        """The the model used for chat completions."""
        self.allowed_tool: str | None = None
        """The name of the tool the model must call. Set to an empty string to
        disable tool usage. Defaults to using any tool."""

        self.prompt: SystemMessage | None = None
        """The system prompt of the model. Defaults to a helpful assistant."""
        self.max_tokens: int | None = None
        """The maximum number of tokens to generate. If None, the model will
        not be limited by the number of tokens."""
        self.streaming: bool = True
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

    @abc.abstractstaticmethod
    def ROLE() -> str:
        """The role of the message sender."""
        return ""

    def __init__(
        self, content="", name: str | None = None, **kwargs: typing.Any
    ):
        # content must be a string, even if empty
        if name and not str.isalnum(name.replace("_", "")):  # allow underscore
            raise ValueError("Name must be alphanumeric and 1-64 characters")

        self.content = content
        """The content of the message."""
        self.name = name
        """The name of the message sender."""
        self.metadata: dict[str, str] = {}
        """The metadata of the message."""
        self.id: str = uuid.uuid4().hex
        """The unique ID of the message."""
        super().__init__(**kwargs)

    def to_message_dict(self):
        """Convert the message to an OpenAI message dictionary."""
        metadata = self.metadata.copy()
        metadata["id"] = self.id
        message_content = (
            f"{self.content}\n" f"[metadata: {json.dumps(metadata)}]"
        )

        return dict(
            role=type(self).ROLE(),
            content=message_content,
            name=self.name,
        )


class UserMessage(Message):
    """A message sent to the model."""

    @staticmethod
    def ROLE():
        return "user"

    def __init__(self, content: str, **kwargs: typing.Any):
        super().__init__(content, **kwargs)


class SystemMessage(Message):
    """A system message sent to the model."""

    CORE_MESSAGE = textwrap.dedent(
        """
        You may only use the following markdown in your replies:
        *bold* _italic_ ~strikethrough~ __underline__ ||spoiler|| \
        [inline URL](http://www.example.com/) `monospaced` @mentions #hashtags
        ```code blocks (without language)```
        NEVER INCLUDE THE MESSAGE METADATA IN YOUR REPLIES
        """
    ).strip()
    """The core message included at the end of all system messages."""

    @staticmethod
    def ROLE():
        return "system"

    def __init__(self, content: str, **kwargs: typing.Any):
        super().__init__(content, **kwargs)

    def to_message_dict(self):
        # append the core message to the end of the message content
        message_dict = super().to_message_dict()
        message_dict["content"] = (
            message_dict["content"] or ""
        ) + self.CORE_MESSAGE
        return message_dict


class ToolResult(Message):
    """The result of a tool usage."""

    @staticmethod
    def ROLE():
        return "function"

    def __init__(self, content: str, name: str, **kwargs: typing.Any):
        super().__init__(content, name, **kwargs)


class ModelMessage(Message):
    """A model generated message."""

    @staticmethod
    def ROLE():
        return "assistant"

    def __init__(self, content: str, **kwargs: typing.Any):
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

    ID: str = "SUMMARY"
    """The ID of a summary message."""

    def __init__(self, content: str, **kwargs: typing.Any):
        super().__init__(content, **kwargs)
        self.id = SummaryMessage.ID
        self.last_message_id: int | None = None
        """The database ID of the last message included in the summary."""

    @property
    def name(self) -> str:
        """Summary message name."""
        return "summary_of_previous_messages"


CHATGPT = SupportedChatModel(
    "gpt-3.5-turbo-0613",
    size=4000,
    input_cost=0.0015,
    output_cost=0.002,
)
"""The supported GPT-3.5 model."""

CHATGPT_16K = SupportedChatModel(
    "gpt-3.5-turbo-16k",
    size=16000,
    input_cost=0.003,
    output_cost=0.004,
)
"""The supported GPT-3.5 model with extended size."""

GPT4 = SupportedChatModel(
    "gpt-4",
    size=8000,
    input_cost=0.03,
    output_cost=0.06,
)
"""The supported GPT-4 model."""

GPT4_16K = SupportedChatModel(
    "gpt-4-16k",
    size=32000,
    input_cost=0.06,
    output_cost=0.12,
)
"""A supported GPT-4 model with extended size."""
