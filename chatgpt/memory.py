"""The memory of models."""

import sqlalchemy.ext.asyncio as async_sql

import chatgpt.core
import chatgpt.events
import chatgpt.openai.chat_model
import chatgpt.openai.supported_models
import chatgpt.openai.tokenization
import database as db
from chatgpt.core import Message, SummaryMessage, SystemMessage

SUMMARIZATION_PROMPT = """\
Progressively summarize the lines of the conversation provided, adding onto \
the previous summary and returning a new summary."""
"""The prompt for summarizing a conversation."""

INSTRUCTIONS = """\
You may only use the following markdown in your replies:
*bold* _italic_ ~strikethrough~ __underline__ ||spoiler|| \
[inline URL](http://www.example.com/) `monospaced` @mentions #hashtags
```code blocks (without language)```"""
"""The core message included at the end of all system messages."""


class ChatMemory:
    """The memory of a chat conversation stored by a session ID."""

    def __init__(
        self,
        chat_history: "ChatHistory",
        short_memory_size: int,
        long_memory_size: int,
        summarization_handlers: list[chatgpt.events.ModelEvent] = [],
    ):
        """Create an uninitialized chat summarization memory."""
        self.memory_size = short_memory_size
        """The max number of tokens the memory can contain."""
        self.history = chat_history
        """The chat history in the memory."""
        self.summarizer = SummarizationModel(
            long_memory_size, handlers=summarization_handlers
        )
        """The summarization model."""

    @classmethod
    async def initialize(
        cls,
        chat_id: str,
        short_memory_size: int,
        long_memory_size: int,
        in_memory: bool = False,
        summarization_handlers: list[chatgpt.events.ModelEvent] = [],
    ):
        """Initialize a chat model memory instance."""
        chat_history = await ChatHistory.initialize(chat_id, in_memory)
        return cls(
            chat_history,
            short_memory_size,
            long_memory_size,
            summarization_handlers,
        )

    @property
    async def summary(self) -> SummaryMessage | None:
        """The summary of the conversation."""
        message = await self.history.get_message(SummaryMessage.ID)
        if message is None:
            return None
        if isinstance(message, SummaryMessage):
            return message
        raise TypeError(f"Expected {SummaryMessage}, got {type(message)}")

    @property
    async def messages(self) -> list[Message]:
        """The messages in the memory."""
        # get all messages except the summary
        (
            short_memory,
            history_messages,
            summary,
        ) = await self._retrieve_messages()

        if self.memory_size < 0:  # unlimited memory
            return _create_prompt(
                (await self.history.model).prompt,
                summary,
                history_messages,
                short_memory,
            )

        # summarize the history
        new_summary = None
        if history_messages:
            new_summary = await self.summarizer.run(summary, history_messages)
        if not new_summary:  # no new summary
            return _create_prompt(
                (await self.history.model).prompt,
                SystemMessage(INSTRUCTIONS),
                summary,
                short_memory,
            )

        # add the new summary to the history
        new_summary.last_message_id = await self.history.get_id(
            history_messages[-1].id
        )
        await self.history.add_message(new_summary)
        return _create_prompt(
            (await self.history.model).prompt, summary, short_memory
        )

    async def _retrieve_messages(
        self,
    ) -> tuple[list[Message], list[Message], SummaryMessage | None]:
        short_memory: list[Message] = []
        history_messages: list[Message] = []
        summary: SummaryMessage | None = None

        # get db messages
        db_messages = await self.history.messages
        db_messages.reverse()  # start from most recent
        last_summarized_id: int | None = None  # id of last summarized message
        for message in db_messages:
            # retrieve the summary
            if isinstance(message, SummaryMessage):
                summary = message
                last_summarized_id = summary.last_message_id
                continue

            # fill the short memory
            new_memory = _create_prompt(message, short_memory)
            if await self._calculate_size(new_memory) < self.memory_size:
                short_memory.insert(0, message)
                continue

            # fill the un-summarized history
            message_id = await self.history.get_id(message.id)
            if last_summarized_id is None:
                history_messages.insert(0, message)
                continue  # un-summarized if no summary exists
            if message_id is None:
                history_messages.insert(0, message)
                continue  # un-summarized if not in history

            # un-summarized if after the last summarized message
            if message_id > last_summarized_id:
                history_messages.insert(0, message)
                continue

            break  # otherwise, the message is summarized, thus not in history

        return short_memory, history_messages, summary

    async def _calculate_size(self, messages: list[Message]) -> int:
        return chatgpt.openai.tokenization.messages_tokens(
            _create_prompt((await self.history.model).prompt, messages),
            (await self.history.model).model,
        )


class ChatHistory:
    """SQL implementation of a chat history stored by a serialized ID."""

    def __init__(self, chat_id: str, engine: async_sql.AsyncEngine | None):
        self.chat_id = chat_id
        """The database chat ID."""
        self.engine = engine
        """The history database engine."""

    @classmethod
    async def initialize(cls, chat_id: str, in_memory=False) -> "ChatHistory":
        engine = None
        if in_memory:  # set up in-memory database
            engine = await db.core.start_engine(db.in_memory)
        # create the chat if it does not exist
        chat = await db.models.Chat(chat_id=chat_id).load()
        await chat.save()
        # return the chat history provider
        return cls(chat_id, engine)

    @property
    async def model(self) -> chatgpt.core.ModelConfig:
        """The model of the chat."""
        chat = await db.models.Chat(chat_id=self.chat_id).load()
        if chat.data is not None:  # otherwise, model does not exist
            return chatgpt.core.ModelConfig.deserialize(chat.data)
        return chatgpt.core.ModelConfig()

    @property
    async def messages(self) -> list[Message]:
        """The messages in the chat history."""
        chat = await db.models.Chat(chat_id=self.chat_id).load()
        db_messages = list(chat.messages)
        db_messages.sort(key=lambda m: m.id)
        return [
            Message.deserialize(db_message.data) for db_message in db_messages
        ]

    async def set_model(self, model: chatgpt.core.ModelConfig | None):
        """Set the model of the chat."""
        chat = await db.models.Chat(chat_id=self.chat_id).load()
        chat.data = model.serialize() if model else None
        await chat.save()

    async def get_message(self, id: str) -> Message | None:
        """Get a message from the chat history."""
        db_message = await db.models.Message(
            message_id=id, chat_id=self.chat_id, engine=self.engine
        ).load()
        if db_message.id is not None:  # otherwise, message does not exist
            return Message.deserialize(db_message.data)
        return None

    async def add_message(self, message: Message):
        """Add a message to the history. Overwrites existing message."""
        db_message = await db.models.Message(
            message_id=message.id,
            chat_id=self.chat_id,
            engine=self.engine,
        ).load()
        db_message.data = message.serialize()
        await db_message.save()

    async def remove_message(self, id: str):
        """Remove a message from the chat history."""
        await db.models.Message(
            message_id=id, chat_id=self.chat_id, engine=self.engine
        ).delete()

    async def get_id(self, message_id: str) -> int | None:
        """Get the database id of a message by its message id."""
        db_message = await db.models.Message(
            message_id=message_id,
            chat_id=self.chat_id,
            engine=self.engine,
        ).load()
        return db_message.id

    async def clear(self) -> None:
        """Clear the chat history."""
        chat = await db.models.Chat(chat_id=self.chat_id).load()
        for message in chat.messages:
            await message.delete()
        # (await message.delete() for message in chat.messages)


class SummarizationModel(chatgpt.openai.chat_model.OpenAIChatModel):
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
            streaming=False,
        )
        super().__init__(config, handlers=handlers)
        self.summary_size = summary_size
        """The max number of tokens a generated summary will contain."""

    async def run(
        self,
        prev_summary: SummaryMessage | None,
        messages: list[Message],
    ) -> SummaryMessage | None:
        """Run the model."""
        # start running the model
        await self.events_manager.trigger_model_run((prev_summary, messages))
        reply = await self._run_model(self._core_logic(prev_summary, messages))
        # check if the model successfully summarized the messages
        if isinstance(reply, chatgpt.core.ModelMessage):
            await self.events_manager.trigger_model_reply(reply)
            reply = SummaryMessage(reply.content)
        # return the reply
        return reply

    async def _core_logic(
        self,
        previous_summary: SummaryMessage | None,
        new_messages: list[Message],
    ) -> chatgpt.core.ModelMessage | None:
        # start with the previous summary or an empty summary
        summary = previous_summary or SummaryMessage("")
        # the summarization prompt of the model
        prompt = _create_prompt(self.config.prompt, summary)

        buffer: list[Message] = []  # the buffer of messages to summarize
        remaining_messages = new_messages[:]  # the messages to summarize
        usage = chatgpt.core.ModelMessage("")  # track usage through a reply

        # summarize messages progressively
        while remaining_messages:
            # take the first remaining message
            message = remaining_messages[0]
            total_size = self._calculate_size(
                _create_prompt(prompt, buffer, message)
            )

            # if the message can fit in the buffer
            if total_size <= self.config.model.size:
                # transfer the message to the buffer and continue
                buffer.append(message)
                remaining_messages.pop(0)
                continue

            else:  # summarize the current buffer otherwise
                new_reply = await self._generate_reply(
                    _create_prompt(prompt, buffer)
                )
                if not isinstance(new_reply, chatgpt.core.ModelMessage):
                    return None  # model failed to generate a summary

                # track the summary generation usage
                usage.prompt_tokens += new_reply.prompt_tokens
                usage.reply_tokens += new_reply.reply_tokens
                usage.cost += new_reply.cost

                # update the summary and model prompt
                summary.content = new_reply.content
                prompt = _create_prompt(prompt, summary)

        # return the summary as a model message
        usage.content = summary.content
        return usage

    def _calculate_size(self, messages: list[Message]) -> int:
        return chatgpt.openai.tokenization.messages_tokens(
            _create_prompt(self.config.prompt, messages),
            (self.config).model,
        )


def _create_prompt(*messages: list | Message | None) -> list[Message]:
    history = []
    for message_item in messages:
        if not message_item:
            continue

        if isinstance(message_item, Message):
            history.append(message_item)

        if isinstance(message_item, list):
            for sub_item in message_item:
                if sub_list := _create_prompt(sub_item):
                    history.extend(sub_list)
    return history
