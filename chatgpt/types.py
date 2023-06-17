"""Types for chatgpt."""

import abc
import enum
import json
import typing

T = typing.TypeVar("T", bound="Serializable")


class Enum(enum.StrEnum):
    @property
    @classmethod
    def values(cls):
        """The values of the enum."""
        return list(map(lambda c: c.value, cls))


class SupportedModel(Enum):
    """The supported GPT models."""

    CHATGPT = "gpt-3.5-turbo-0613"
    """The GPT-3.5 model."""
    CHATGPT_16K = "gpt-3.5-turbo-16k"
    """The GPT-3.5 model with a 16k token limit."""
    GPT4 = "gpt-4"
    """The GPT-4 model."""
    GPT4_32K = "gpt-4-32k"
    """The GPT-4 model with a 32k token limit."""

    @classmethod
    def gpt3_models(cls):
        """The GPT-3.5 models."""
        return [cls.CHATGPT, cls.CHATGPT_16K]

    @classmethod
    def gpt4_models(cls):
        """The GPT-4 models."""
        return [cls.GPT4, cls.GPT4_32K]


class FinishReason(Enum):
    """The possible reasons for a completion to finish."""

    DONE = "stop"
    """The full completion was generated."""
    TOOL_USE = "function_call"
    """The model is using a tool."""
    LIMIT_REACHED = "length"
    """The token limit or maximum completion tokens was reached."""
    FILTERED = "content_filter"
    """Completion content omitted due to content filter."""
    CANCELED = "canceled"
    """The completion was canceled by the user."""
    UNDEFINED = "null"
    """The completion is still in progress or incomplete."""


class Serializable(abc.ABC):
    """An object that can be serialized to a JSON dictionary."""

    def __init__(self, **kwargs):
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
        if not (derivative := _get_subclass(cls, type_name)):
            raise ValueError(
                f"Could not deserialize {type_name} as {cls.__name__}"
            )

        # create instance
        return derivative(**parameters)


class Message(Serializable, abc.ABC):
    """The base of all messages sent to a model."""

    ROLE: str
    """The role of the message sender."""

    def __init__(self, content: str, name: str | None = None, **kwargs):
        if name and not str.isalnum(name.replace("_", "")):  # allow underscore
            raise ValueError("Name must be alphanumeric and 1-64 characters")

        self.name = name
        """The name of the message sender."""
        self.content = content
        """The content of the message."""
        super().__init__(**kwargs)

    def to_message_dict(self):
        message = dict(
            role=type(self).ROLE,
            content=self.content,
            name=self.name,
        )
        return {k: v for k, v in message.items() if v is not None}


def _get_subclass(base_class, subclass_name):
    for subclass in base_class.__subclasses__():
        if subclass.__name__ == subclass_name:
            return subclass
        else:  # recursively check the subclasses of the subclass
            result = _get_subclass(subclass, subclass_name)
            if result and issubclass(result, base_class):
                return result
    return None
