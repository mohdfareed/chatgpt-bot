"""Tools available to models."""

import inspect
import io
import sys
import typing

import wikipedia
from langchain.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper
from typing_extensions import override

import chatgpt.addons
import chatgpt.core
import chatgpt.events
import chatgpt.tools
from bot import SERPER_API_KEY


class InternetSearch(chatgpt.tools.Tool):
    """A tool for searching the internet."""

    @property
    def name(self):
        return "internet_search"

    @property
    def description(self):
        return (
            "Search the internet. Useful for finding up-to-date information "
            "about current events."
        )

    @property
    def parameters(self):
        return [
            chatgpt.tools.ToolParameter(
                name="query",
                type="string",
                description="A targeted search query.",
            ),
        ]

    @override
    async def _run(self, query: str) -> str:
        return await GoogleSerperAPIWrapper(
            serper_api_key=SERPER_API_KEY
        ).arun(query)


class WikiSearch(chatgpt.tools.Tool):
    """A tool for searching Wikipedia."""

    @property
    def name(self):
        return "wiki_search"

    @property
    def description(self):
        return (
            "Search Wikipedia. Useful for finding information about new or "
            "or unknown subjects and topics."
        )

    @property
    def parameters(self):
        return [
            chatgpt.tools.ToolParameter(
                name="query",
                type="string",
                description="A targeted search query or subject.",
            ),
        ]

    async def _run(self, query: str) -> str:
        wiki_client = WikipediaAPIWrapper(wiki_client=wikipedia)
        return wiki_client.run(query)


class Python(chatgpt.tools.Tool):
    """A tool for executing Python code."""

    @property
    def name(self):
        return "python"

    @property
    def description(self):
        return (
            "Execute Python code. Useful for performing complex calculations"
            "and tasks. Equivalent to running in a Python shell. Only use it "
            "to run safe code. Can't include async code. Everything returned "
            "must be printed."
        )

    @property
    def parameters(self):
        return [
            chatgpt.tools.ToolParameter(
                type="string",
                name="code",
                description="The Python code to execute.",
            ),
        ]

    @override
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


def available_tools(
    tool=chatgpt.tools.Tool,
) -> typing.Iterator[chatgpt.tools.Tool]:
    """Returns all the available tools."""
    if not inspect.isabstract(tool):
        yield tool()  # type: ignore
    for sub_tool in tool.__subclasses__():
        yield from available_tools(sub_tool)


def from_tool_name(tool_name: str):
    """Get a tool by name."""
    for tool in available_tools():
        if tool.name == tool_name:
            return tool
    raise ValueError("Invalid tool name")
