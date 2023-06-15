"""The possible memory implementations of agents."""

import json
from typing import Any, Dict, List

import sqlalchemy as sql
from langchain import chat_models as langchain_models
from langchain import memory as langchain_memory
from langchain import prompts as langchain_prompts
from langchain import schema as langchain_schema
from langchain.memory.chat_message_histories import sql as langchain_sql
from sqlalchemy import orm
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine

import database as db
from chatgpt import OPENAI_API_KEY

CHAT_HISTORY_STRING = """\
Summary:
{summary}

Recent messages:
{messages}
"""
"""The format of the chat history."""

SUMMARIZATION_PROMPT = langchain_prompts.PromptTemplate(
    input_variables=["summary", "new_lines"],
    template="""\
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
{summary}

New lines of conversation:
{new_lines}

New summary:
""",
)
"""The prompt for summarizing a conversation."""


class ChatMemory(langchain_memory.ConversationSummaryBufferMemory):
    """A memory of a chat conversation stored by a session ID."""

    summary = ""
    """The current summary of the conversation."""
    internal_buffer: List[langchain_schema.BaseMessage] = []

    @property
    def buffer(self) -> List[langchain_schema.BaseMessage]:
        self.prune()
        return self.internal_buffer

    def __init__(
        self,
        token_limit: int,
        url: str = db.url,
        session_id: str = "",
        openai_api_key: str = OPENAI_API_KEY,
    ):
        """Initialize a chat summarization memory. Defaults to an in-memory
        implementation if no session ID is provided.

        Args:
            token_limit (int): Max number of tokens history can contain.
            url (str): SQL database URL.
            session_id (str, optional): Memory session ID.
        """

        # set in-memory implementation if no session ID is provided
        if not session_id:
            url = "sqlite:///:memory:"

        # create summarization model
        model = langchain_models.ChatOpenAI(
            openai_api_key=openai_api_key,
        )  # type: ignore

        # create summarization memory
        super().__init__(
            llm=model,
            prompt=SUMMARIZATION_PROMPT,
            memory_key="chat_history",
            max_token_limit=(token_limit - 8),  # history + summary
        )

        # setup chat history
        self.chat_memory = ChatHistory(session_id, url)
        self.internal_buffer = self.chat_memory.messages

    @classmethod
    def delete(cls, url: str, session: str) -> None:
        """Delete the memory of a session."""

        memory = cls(-1, url, session)
        memory.chat_memory.clear()

    @classmethod
    def store(cls, message: str, url: str, session: str) -> None:
        """Store the memory of a session."""

        memory = cls(-1, url, session)
        memory.chat_memory.add_user_message(message)

    def load_memory_variables(self, _: Dict[str, Any]) -> Dict[str, Any]:
        buffer = self.buffer
        if self.moving_summary_buffer != "":
            first_messages: List[langchain_schema.BaseMessage] = [
                self.summary_message_cls(content=self.moving_summary_buffer)
            ]
            buffer = first_messages + buffer

        final_buffer = self._get_chat_buffer_string(buffer)
        return {self.memory_key: final_buffer}

    def prune(self) -> None:
        buffer = self.chat_memory.messages
        curr_buffer_length = self.llm.get_num_tokens_from_messages(buffer)
        if curr_buffer_length > self.max_token_limit:
            pruned_memory = []
            while curr_buffer_length > self.max_token_limit:
                pruned_memory.append(buffer.pop(0))
                curr_buffer_length = self.llm.get_num_tokens_from_messages(
                    buffer
                )
            self.moving_summary_buffer = self.predict_new_summary(
                pruned_memory, self.moving_summary_buffer
            )
        self.internal_buffer = buffer

    def _get_chat_buffer_string(self, messages: List) -> str:
        string_messages = "\n"
        for m in messages:
            if isinstance(m, self.summary_message_cls):
                string_messages += "Summary:\n\n"
                string_messages += f"{m.content}\n\n"
                string_messages += "Recent History:\n\n"
            else:
                string_messages += m.content
        return string_messages  # costs 6 tokens


class ChatHistory(langchain_schema.BaseChatMessageHistory):
    """SQL implementation of a chat history stored by a session ID."""

    class _Base(orm.DeclarativeBase):
        pass

    def __init__(self, session_id: str):
        self._Base.metadata.create_all(self.engine)
        self.session_id = session_id

    @property
    def messages(self) -> List[langchain_schema.BaseMessage]:
        with orm.Session(db.engine()) as session:
            result = session.query(self.Message).where(
                self.Message.session_id == self.session_id
            )
            items = [json.loads(record.message) for record in result]
            messages = langchain_schema.messages_from_dict(items)
            return messages

    def add_message(self, message: langchain_schema.BaseMessage) -> None:
        with orm.Session(db.engine()) as session:
            json_str = json.dumps(langchain_schema._message_to_dict(message))
            session.add(
                self.Message(session_id=self.session_id, message=json_str)
            )
            session.commit()

    def clear(self) -> None:
        with orm.Session(db.engine()) as session:
            session.query(self.Message).filter(
                self.Message.session_id == self.session_id
            ).delete()
            session.commit()
