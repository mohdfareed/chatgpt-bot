"""The messages that can be sent to and return by a model."""

import abc
import json
import typing
import uuid

from typing_extensions import override

from chatgpt import core


class Message(core.Serializable, abc.ABC):
    """The base of all messages sent to a model."""

    METADATA_DELIMITER = "<|METADATA|>"

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
        self.pinned: bool = False
        """Whether the message is pinned. Pinned messages are not deleted."""
        super().__init__(**kwargs)

    def to_message_dict(self):
        """Convert the message to an OpenAI message dictionary."""
        metadata = self.metadata.copy()
        metadata["id"] = self.id
        message_content = (
            self.content + Message.METADATA_DELIMITER + json.dumps(metadata)
        )

        return dict(
            role=type(self).ROLE(),
            content=message_content,
            name=self.name,
        )


class UserMessage(Message):
    """A message sent to the model."""

    @override
    @staticmethod
    def ROLE():
        return "user"

    def __init__(self, content: str, **kwargs: typing.Any):
        super().__init__(content, **kwargs)


class SystemMessage(Message):
    """A system message sent to the model."""

    @override
    @staticmethod
    def ROLE():
        return "system"

    def __init__(self, content: str, **kwargs: typing.Any):
        super().__init__(content, **kwargs)


class ToolResult(Message):
    """The result of a tool usage."""

    @override
    @staticmethod
    def ROLE():
        return "function"

    def __init__(self, content: str, name: str, **kwargs: typing.Any):
        super().__init__(content, name, **kwargs)


class ModelMessage(Message):
    """A model generated message."""

    @override
    @staticmethod
    def ROLE():
        return "assistant"

    def __init__(self, content: str, **kwargs: typing.Any):
        self.finish_reason = core.FinishReason.UNDEFINED
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
        return json.loads(self.args_str or "{}")

    @override
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

    @name.setter
    def name(self, value: str):
        pass  # implement to adhere to interface
