"""The possible memory implementations of agents."""

import os
from typing import Any, Dict, List

from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationSummaryBufferMemory
from langchain.memory.chat_message_histories import file, in_memory, sql
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage

from chatgpt import OPENAI_API_KEY

SUMMARY_MEMORY = PromptTemplate(
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


class ChatMemory(ConversationSummaryBufferMemory):
    """A memory of a chat conversation."""

    internal_buffer: List[BaseMessage] = []

    @property
    def buffer(self) -> List[BaseMessage]:
        self.prune()
        return self.internal_buffer

    def __init__(
        self,
        token_limit: int,
        url: str | None = None,
        session_id: str | None = None,
        openai_api_key: str = OPENAI_API_KEY,
    ):
        """Initialize a chat summarization memory. Defaults to an in-memory
        implementation.

        Args:
            token_limit (int): Max number of tokens history can contain.
            url (str, optional): SQL database URL.
            session_id (str, optional): Memory session ID in the database.
        """

        # create summarization memory
        super().__init__(
            llm=ChatOpenAI(openai_api_key=openai_api_key),  # type: ignore
            prompt=SUMMARY_MEMORY,
            memory_key="chat_history",
            max_token_limit=(token_limit - 8),  # history + summary
        )

        # setup chat history
        if url and session_id:  # connect to database if provided
            self.chat_memory = sql.SQLChatMessageHistory(session_id, url)
        else:  # initialize in-memory history
            self.chat_memory = in_memory.ChatMessageHistory()
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
            first_messages: List[BaseMessage] = [
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

    def _get_chat_buffer_string(self, messages: List[BaseMessage]) -> str:
        string_messages = "\n"
        for m in messages:
            if isinstance(m, self.summary_message_cls):
                string_messages += "Summary:\n\n"
                string_messages += f"{m.content}\n\n"
                string_messages += "Recent History:\n\n"
            else:
                string_messages += m.content
        return string_messages  # costs 6 tokens
