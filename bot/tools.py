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
    @override
    def title(self):
        return "Internet Search"

    @property
    @override
    def name(self):
        return "internet_search"

    @property
    @override
    def description(self):
        return (
            "Search the internet. Useful for finding up-to-date information "
            "about current events."
        )

    @property
    @override
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
    @override
    def title(self):
        return "Wikipedia Search"

    @property
    @override
    def name(self):
        return "wiki_search"

    @property
    @override
    def description(self):
        return (
            "Search Wikipedia. Useful for finding information about new or "
            "or unknown subjects and topics."
        )

    @property
    @override
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
    @override
    def title(self):
        return "Python Interpreter"

    @property
    @override
    def name(self):
        return "python"

    @property
    @override
    def description(self):
        return (
            "Execute Python code. Useful for performing complex calculations"
            "and tasks. Equivalent to running in a Python shell. Only use it "
            "to run safe code. Can't include async code. Everything returned "
            "must be printed."
        )

    @property
    @override
    def parameters(self):
        return [
            chatgpt.tools.ToolParameter(
                type="string",
                name="code",
                description="The Python code to execute.",
            ),
        ]

    @override
    async def _run(self, code: str) -> str:
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


def available_tools(tool=chatgpt.tools.Tool) -> list[chatgpt.tools.Tool]:
    """Returns all the available tools."""
    from chatgpt import addons, tools

    all_tools: list[chatgpt.tools.Tool] = []
    if not inspect.isabstract(tool):
        all_tools.append(tool())  # type: ignore
    for sub_tool in tool.__subclasses__():
        all_tools.extend(available_tools(sub_tool))
    return all_tools


def from_tool_name(tool_name: str):
    """Get a tool by name."""
    for tool in available_tools():
        if tool.name == tool_name:
            return tool
    raise ValueError("Invalid tool name")
