"""Core types and classes for ChatGPT."""

import abc
import enum
import json
import typing

T = typing.TypeVar("T", bound="Serializable")


class ChatModel(abc.ABC):
    """A chat model."""

    @abc.abstractmethod
    def stop():
        """Stop the model."""


class ModelError(Exception):
    """Exception raised for model errors."""


class FinishReason(enum.StrEnum):
    """The possible reasons for a completion to finish."""

    DONE = "stop"
    """The full completion was generated."""
    TOOL_USE = "function_call"
    """The model is using a tool."""
    LIMIT_REACHED = "length"
    """The token limit or maximum completion tokens was reached."""
    CENSORED = "content_filter"
    """Completion content omitted due to content filter."""
    CANCELLED = "canceled"
    """The completion was canceled by the user."""
    UNDEFINED = "null"
    """The completion is still in progress or incomplete."""


class Serializable(abc.ABC):
    """An object that can be serialized to a JSON dictionary string. Supports
    nested objects, basic types, lists, and dictionaries."""

    def __init__(self, **kwargs: typing.Any):
        self.__dict__.update(kwargs)

    def serialize(self) -> str:
        """Get the object as a serialized string."""
        serialized_dict = {
            # store the type's fully-qualified name to allow deserialization
            "serialized_type": type(self).__qualname__,
            # recursively serialize all serializable attributes
            "serialized_params": {
                key: Serializable._serialize_value(value)
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

        # deserialize parameters and create instance
        for key, value in parameters.items():
            parameters[key] = Serializable._deserialize_value(value)
        return derivative(**parameters)

    @staticmethod
    def _serialize_value(value: typing.Any) -> typing.Any:
        if isinstance(value, Serializable):
            return value.serialize()
        elif isinstance(value, list):
            return [Serializable._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {
                k: Serializable._serialize_value(v) for k, v in value.items()
            }
        else:
            return value

    @staticmethod
    def _deserialize_value(value: typing.Any) -> typing.Any:
        if isinstance(value, str):
            try:
                potential_object_dict = json.loads(value)
                if (
                    isinstance(potential_object_dict, dict)
                    and "serialized_type" in potential_object_dict
                ):
                    return Serializable.deserialize(value)
            except json.JSONDecodeError:
                pass
        elif isinstance(value, list):
            return [Serializable._deserialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {
                k: Serializable._deserialize_value(v) for k, v in value.items()
            }
        return value

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


class ModelConfig(Serializable):
    """ChatGPT model configuration and parameters."""

    def __init__(self, **kwargs: typing.Any) -> None:
        import chatgpt.messages
        import chatgpt.tools

        self.chat_model = CHATGPT
        """The the chat model used for chat completions."""
        self.tools: list[chatgpt.tools.Tool] = []
        """The tools available to the model."""
        self.allowed_tool: str | None = None
        """The name of the tool the model must call. Set to an empty string to
        disable tool usage. Defaults to using any tool."""

        self.prompt: chatgpt.messages.SystemMessage | None = None
        """The system prompt of the model. Defaults to a helpful assistant."""
        self.max_tokens: int | None = None
        """The maximum number of tokens to generate. If None, the model will
        not be limited by the number of tokens."""
        self.streaming: bool = True
        """Whether the model streams completions as they are generated."""
        self.stop_sequences: list[
            str
        ] | str = chatgpt.messages.Message.METADATA_DELIMITER
        """A list of sequences at which to stop reply generation. """

        self.temperature: float = 1.0
        """Tokens confidence threshold, in range [0.0, 2.0]."""
        self.presence_penalty: float = 0.0
        """Penalty for repeated tokens, in range [-2.0, 2.0]."""
        self.frequency_penalty: float = 0.0
        """Tokens penalty based on usage frequency, in range [-2.0, 2.0]."""
        super().__init__(**kwargs)

    def to_dict(self) -> dict[str, str | float | list[str] | None]:
        """Convert the model configuration to an OpenAI dictionary."""
        func_call = "none" if self.allowed_tool == "" else self.allowed_tool
        return dict(
            model=self.chat_model.name,
            function_call=func_call,
            max_tokens=self.max_tokens,
            stop=self.stop_sequences,
            temperature=self.temperature,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            stream=self.streaming,
        )

    @staticmethod
    def supported_models():
        """Return a list of all supported chat models."""
        return [CHATGPT, CHATGPT_16K, GPT4]

    @staticmethod
    def model(name: str):
        """Return a supported chat model by name."""
        for model in ModelConfig.supported_models():
            if model.name == name:
                return model
        raise ValueError(f"Unsupported chat model: {name}")


class SupportedChatModel(Serializable):
    """A supported GPT model."""

    def __init__(
        self,
        name: str,
        title: str = "",
        size=0,
        input_cost=0.0,
        output_cost=0.0,
        **kwargs: typing.Any,
    ):
        self.name = name
        """The name of the model."""
        self.title = title or name
        """The title of the model. Defaults to the name of the model."""
        self.size = size
        """The size of input the model can accept in tokens."""
        self.input_cost = input_cost
        """The cost of input tokens, in USD and per 1k tokens."""
        self.output_cost = output_cost
        """The cost of output tokens, in USD and per 1k tokens."""
        super().__init__(**kwargs)


CHATGPT = SupportedChatModel(
    "gpt-3.5-turbo-0613",
    title="GPT-3.5 Turbo",
    size=4000,
    input_cost=0.0015,
    output_cost=0.002,
)
"""The supported GPT-3.5 model."""

CHATGPT_16K = SupportedChatModel(
    "gpt-3.5-turbo-16k",
    title="GPT-3.5 Turbo 16k",
    size=16000,
    input_cost=0.003,
    output_cost=0.004,
)
"""The supported GPT-3.5 model with extended size."""

GPT4 = SupportedChatModel(
    "gpt-4",
    title="GPT-4",
    size=8000,
    input_cost=0.03,
    output_cost=0.06,
)
"""The supported GPT-4 model."""

GPT4_32K = SupportedChatModel(
    "gpt-4-32k",
    title="GPT-4 32k",
    size=32000,
    input_cost=0.06,
    output_cost=0.12,
)
"""A supported GPT-4 model with extended size."""
