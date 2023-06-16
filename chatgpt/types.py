"""Types for chatgpt."""

import abc
import enum
import json
import re


class Enum(enum.StrEnum):
    @property
    @classmethod
    def values(cls):
        """The values of the enum."""
        return list(map(lambda c: c.value, cls))


class SupportedModel(Enum):
    """The supported GPT models."""

    CHATGPT = "gpt-3.5-turbo"
    """The GPT-3.5 model."""
    CHATGPT_16K = "gpt-3.5-turbo-16k"
    """The GPT-3.5 model with a 16k token limit."""
    GPT4 = "gpt-4"
    """The GPT-4 model."""
    GPT4_32K = "gpt-4-32k"
    """The GPT-4 model with a 32k token limit."""

    @property
    @classmethod
    def gpt3(cls):
        """The GPT-3.5 models."""
        return [cls.CHATGPT, cls.CHATGPT_16K]

    @property
    @classmethod
    def gpt4(cls):
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

    def to_json(self):
        """Get the object as a JSON dictionary."""
        return json.dumps(self.__dict__)

    def from_json(self, model_json: str):
        """Load the object from a JSON dictionary of parameters."""
        json_dict: dict = json.loads(model_json)
        self.__dict__.update(json_dict)
        return self


class Message(Serializable, abc.ABC):
    """The base of all messages."""

    ROLE: str

    def __init__(self, content: str):
        super().__init__()
        self._name = None
        self.content = content
        """The content of the message."""

    @property
    def name(self):
        """The name of the message sender."""
        return self._name

    @name.setter
    def name(self, name: str | None):
        pattern = r"^\w{1,64}$"
        if name and not re.match(pattern, name):
            raise ValueError("Name must be alphanumeric and 1-64 characters")
        self._name = name

    def to_message_dict(self):
        """Get the message as a dictionary for use in generation requests."""
        message = dict(
            role=type(self).ROLE,
            content=self.content,
            name=self.name,
        )
        return {k: v for k, v in message.items() if v is not None}


class Reply(Serializable, abc.ABC):
    """The base of all model generated replies."""

    def __init__(self):
        super().__init__()
        self.finish_reason: FinishReason = FinishReason.UNDEFINED
        """The finish reason of the reply generation."""
        self.prompt_tokens: int = 0
        """The number of tokens in the prompt provided."""
        self.reply_tokens: int = 0
        """The number of tokens in the reply generated."""
        self.cost: float = 0.0
        """The cost of the reply generation, in USD."""

    @abc.abstractmethod
    def to_message_dict(self) -> dict[str, str]:
        """Get the message as a dictionary for use in generation requests."""
        pass
