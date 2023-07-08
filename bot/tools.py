"""Tools available to models."""

import io
import sys

import wikipedia
from langchain.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper

import chatgpt.core
import chatgpt.events
import chatgpt.tools
from bot import SERPER_API_KEY


class InternetSearch(chatgpt.tools.Tool):
    """A tool for searching the internet."""

    def __init__(self):
        self.name = "internet_search"
        self.description = (
            "Search the internet. Useful for finding up-to-date information "
            "about current events."
        )

        self.parameters = [
            chatgpt.tools.ToolParameter(
                type="string",
                name="query",
                description="A targeted search query.",
            ),
        ]

    async def _run(self, query: str) -> str:
        return await GoogleSerperAPIWrapper(
            serper_api_key=SERPER_API_KEY
        ).arun(query)


class WikiSearch(chatgpt.tools.Tool):
    """A tool for searching Wikipedia."""

    def __init__(self):
        self.name = "wiki_search"
        self.description = (
            "Search Wikipedia. Useful for finding information about new or "
            "or unknown subjects and topics."
        )

        self.parameters = [
            chatgpt.tools.ToolParameter(
                type="string",
                name="query",
                description="A targeted search query or subject.",
            ),
        ]

    async def _run(self, query: str) -> str:
        wiki_client = WikipediaAPIWrapper(wiki_client=wikipedia)
        return wiki_client.run(query)


class Python(chatgpt.tools.Tool):
    """A tool for executing Python code."""

    def __init__(self):
        self.name = "python"
        self.description = (
            "Execute Python code. Useful for performing complex calculations"
            "and tasks. Equivalent to running in a Python shell. Only use it "
            "to run safe code. Can't include async code. Everything returned "
            "must be printed."
        )

        self.parameters = [
            chatgpt.tools.ToolParameter(
                type="string",
                name="code",
                description="The Python code to execute.",
            ),
        ]

    def _run(self, code: str) -> str:
        local_vars = {}
        buffer = io.StringIO()
        stdout = sys.stdout
        sys.stdout = buffer

        try:
            exec(code, {}, local_vars)
        finally:
            sys.stdout = stdout

        output = buffer.getvalue()
        return (output or "").strip()
