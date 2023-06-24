"""The memory of models."""

import chatgpt.core
import chatgpt.events
import chatgpt.openai
import chatgpt.supported_models
import chatgpt.tokenization
import database as db

SUMMARIZATION_PROMPT = """\
Progressively summarize the lines of the conversation provided, adding onto \
the previous summary and returning a new summary."""
"""The prompt for summarizing a conversation."""


class ChatMemory:
    """The memory of a chat conversation stored by a session ID."""

    SUMMARY_MESSAGE_ID = -1
    """The ID of the summary message in the chat history."""

    def __init__(
        self,
        session_id: str,
        short_memory_size: int,
        long_memory_size: int,
        tokenization_model: chatgpt.supported_models.SupportedModel,
        im_memory: bool = False,
    ):
        """Initialize a chat summarization memory."""

        self.memory_size = short_memory_size
        """The max number of tokens the memory can contain."""
        self.tokenization_model = tokenization_model
        """The model used for counting tokens against the memory size."""
        self.history = ChatHistory(session_id, im_memory)
        """The chat history in the memory."""

        # create summarization model
        self.summarizer = SummarizationModel(long_memory_size)
        """The summarization model."""

    @property
    def summary(self) -> "chatgpt.core.SummaryMessage":
        """The summary of the conversation."""
        message = self.history.get_message(self.SUMMARY_MESSAGE_ID)
        return chatgpt.core.SummaryMessage.deserialize(message.serialize())

    @summary.setter
    def summary(self, text: str):
        self.history.remove_message(self.SUMMARY_MESSAGE_ID)
        new_summary = chatgpt.core.SummaryMessage(text)
        self.history.add_message(new_summary, ChatMemory.SUMMARY_MESSAGE_ID)

    @property
    def messages(self) -> list[chatgpt.core.Message]:
        """The messages in the memory."""
        if self.memory_size < 0:  # unlimited memory
            return self.history.messages

        buffer = self.history.messages
        buffer_size = chatgpt.tokenization.messages_tokens(
            buffer, self.tokenization_model
        )

        pruned_memory: list[chatgpt.core.Message] = []
        while buffer_size > self.memory_size:
            pruned_memory.append(buffer.pop(0))
            buffer_size = chatgpt.tokenization.messages_tokens(
                buffer, self.tokenization_model
            )

        # REVIEW: loop over buffer until size of both the buffer and summary
        # combined is less than memory_size. Each iteration, keep popping from
        # the buffer until the combined size is less than memory_size. Then
        # summarize the popped messages along the current summary. Keep
        # repeating until both the summary and buffer are under memory_size.
        # internal summarizer uses the same technique to summarize the buffer
        # if it is too large (internally defined size).

        # self.summary = self._summarize(pruned_memory)
        return [self.summary] + buffer


class ChatHistory:
    """SQL implementation of a chat history stored by a session ID."""

    def __init__(self, session_id: str, im_memory=False):
        memory_engine = (  # set up in-memory database
            db.core.start_engine("sqlite:///:memory:") if im_memory else None
        )
        self.engine = memory_engine
        self.session_id = session_id

    @property
    def messages(self) -> list[chatgpt.core.Message]:
        """The messages in the chat history."""
        messages = db.models.Message.load_messages(
            session_id=self.session_id, engine=self.engine
        )
        return [
            chatgpt.core.Message.deserialize(db_message.content)
            for db_message in messages
        ]

    def get_message(self, message_id: int) -> chatgpt.core.Message:
        """Get a message from the chat history."""
        db_message = db.models.Message(
            id=message_id, session_id=self.session_id, engine=self.engine
        ).load()
        return chatgpt.core.Message.deserialize(db_message.content)

    def add_message(
        self, message: chatgpt.core.Message, message_id: int | None = None
    ):
        """Add a message to the chat history."""
        # TODO: provide custom ID for message
        db.models.Message(
            self.session_id,
            id=message_id,
            content=message.serialize(),
            engine=self.engine,
        ).save()

    def remove_message(self, message_id: int):
        """Remove a message from the chat history."""
        db.models.Message(
            id=message_id, session_id=self.session_id, engine=self.engine
        ).delete()

    def clear(self) -> None:
        """Clear the chat history."""
        (
            message.delete()
            for message in db.models.Message.load_messages(
                self.session_id, engine=self.engine
            )
        )


class SummarizationModel(chatgpt.openai.OpenAIModel):
    """Chat history summarization model."""

    def __init__(
        self,
        summary_size: int,
        summarization_prompt=SUMMARIZATION_PROMPT,
        temperature=0.9,
        handlers: list[chatgpt.events.ModelEvent] = [],
    ):
        config = chatgpt.core.ModelConfig(
            temperature=temperature,
            prompt=summarization_prompt,
            max_tokens=summary_size,
        )
        super().__init__(config, handlers=handlers)
        self.summary_size = summary_size
        """The max number of tokens the summary can contain."""

    async def run(
        self,
        prev_summary: chatgpt.core.SummaryMessage,
        messages: list[chatgpt.core.Message],
    ) -> chatgpt.core.SummaryMessage | None:
        """Run the model."""
        # start running the model
        await self.events_manager.trigger_model_run((prev_summary, messages))
        reply = await self._run_model(self._core_logic(prev_summary, messages))
        # check if the model successfully summarized the messages
        if isinstance(reply, chatgpt.core.ModelMessage):
            await self.events_manager.trigger_model_reply(reply)
            reply = chatgpt.core.SummaryMessage(reply.content)
        # return the reply
        return reply

    async def _core_logic(
        self,
        previous_summary: chatgpt.core.SummaryMessage,
        new_messages: list[chatgpt.core.Message],
    ) -> chatgpt.core.ModelMessage | None:
        messages = [previous_summary] + new_messages
        reply = await self._generate_reply(messages)
        return reply

        # # the buffer of messages to add to the summary
        # buffer: list[chatgpt.core.Message] = [previous_summary]
        # buffer_size = chatgpt.tokenization.messages_tokens(
        #     buffer, self.config.model
        # )
        # # the remaining messages to summarize
        # remaining_messages = new_messages[:]

        # # summarize messages progressively
        # while remaining_messages:
        #     # take the first remaining message
        #     message = remaining_messages[0]
        #     message_size = calculate_size(message)

        #     # If the size of the messages to summarize and the size of the message do not exceed the maximum size
        #     if buffer_size + message_size <= self.config.max_tokens:
        #         # Add the message to the messages to summarize
        #         buffer.append(message)

        #         # Add the size of the message to the size to summarize
        #         buffer_size += message_size

        #         # Remove the message from the remaining messages
        #         remaining_messages.pop(0)
        #     else:
        #         # Summarize the messages to summarize
        #         summary = summarize(messages_to_summarize)

        #         # Update the list of messages to summarize with the summary
        #         messages_to_summarize = [summary]

        #         # Update the size of the messages to summarize with the size of the summary
        #         buffer_size = calculate_size(summary)

        # # Summarize the remaining messages to summarize
        # summary = summarize(messages_to_summarize)

        # # Return the summary
        # return summary
