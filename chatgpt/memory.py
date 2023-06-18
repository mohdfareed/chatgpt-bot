"""The memory of models."""

import chatgpt.core
import chatgpt.utils
import database as db

SUMMARIZATION = """\
Progressively summarize the lines of the conversation provided, adding onto \
the previous summary and returning a new summary.

EXAMPLE

Current summary:
Person asks what you think of artificial intelligence. You think artificial \
intelligence is a force for good.

New lines of conversation:
Person: Why do you think artificial intelligence is a force for good?
You: Because it will help humans reach their full potential.

New summary:
Person asks what the you think of artificial intelligence. You think \
artificial intelligence is a force for good because it will help humans reach \
their full potential.

END OF EXAMPLE

Current summary:
{0}

New lines of conversation:
{1}

New summary:
"""
"""The prompt for summarizing a conversation."""


class ChatMemory:
    """The memory of a chat conversation stored by a session ID."""

    SUMMARY_MESSAGE_ID = -1
    """The ID of the summary message in the chat history."""

    @property
    def summary(self) -> "chatgpt.core.SummaryMessage":
        """The summary of the conversation."""
        message = self.chat_history.get_message(self.SUMMARY_MESSAGE_ID)
        return chatgpt.core.SummaryMessage.deserialize(message.serialize())

    @summary.setter
    def summary(self, text: str):
        self.chat_history.remove_message(self.SUMMARY_MESSAGE_ID)
        self.chat_history.add_message(chatgpt.core.SummaryMessage(text))

    def __init__(
        self,
        session_id: str,
        tokenization_model: chatgpt.core.SupportedModel,
        memory_size=-1,
    ):
        """Initialize a chat summarization memory."""

        self.size = memory_size
        """The max number of tokens the memory can contain."""
        self.tokenization_model = tokenization_model
        self.chat_history = ChatHistory(session_id)
        """The chat history in the memory."""

        # create summarization model
        self.model = chatgpt.core.ModelConfig()
        """The summarization model configuration."""
        self.prompt = chatgpt.core.Prompt(SUMMARIZATION, ["summary", "chat"])
        """The summarization prompt."""

    @property
    def messages(self) -> list[chatgpt.core.Message]:
        """The messages in the memory."""
        # the conversation is the history + the summary such that the total
        # number of tokens is less than the memory size
        # messages = [self.summary] + self.chat_history.messages

        # while self._tokens_size(messages) > self.size:
        #     # TODO: summarize and remove the oldest message
        #     messages.pop()

        return self.chat_history.messages

    def _tokens_size(self, messages: list[chatgpt.core.Message]) -> int:
        messages_dicts = [message.to_message_dict() for message in messages]
        return chatgpt.utils.messages_tokens(
            messages_dicts, self.tokenization_model
        )


class ChatHistory:
    """SQL implementation of a chat history stored by a session ID."""

    def __init__(self, session_id: str):
        self.session_id = session_id

    @property
    def messages(self) -> list[chatgpt.core.Message]:
        """The messages in the chat history."""
        messages = db.models.Message.load_messages(self.session_id)
        return [
            chatgpt.core.Message.deserialize(db_message.content)
            for db_message in messages
        ]

    def get_message(self, message_id: int) -> chatgpt.core.Message:
        """Get a message from the chat history."""
        db_message = db.models.Message(
            id=message_id, session_id=self.session_id
        ).load()
        return chatgpt.core.Message.deserialize(db_message.content)

    def add_message(self, message: chatgpt.core.Message):
        """Add a message to the chat history."""
        db.models.Message(self.session_id, content=message.serialize()).save()

    def remove_message(self, message_id: int):
        """Remove a message from the chat history."""
        db.models.Message(id=message_id, session_id=self.session_id).delete()

    def load(self, messages: list[chatgpt.core.Message]) -> None:
        """Load the chat history into the database."""
        for message in messages:
            self.add_message(message)

    def clear(self) -> None:
        """Clear the chat history."""
        for message in db.models.Message.load_messages(self.session_id):
            message.delete()
