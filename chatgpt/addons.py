"""Addon implementations for ChatGPT."""

import io
import sys

import rich
import rich.console
import wikipedia
from langchain import LLMMathChain, OpenAI
from langchain.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper

import chatgpt.core
import chatgpt.events
import chatgpt.tools
from chatgpt import OPENAI_API_KEY, SERPER_API_KEY


class ConsoleHandler(
    chatgpt.events.ModelStart,
    chatgpt.events.ToolUse,
    chatgpt.events.ToolResult,
    chatgpt.events.ModelReply,
    chatgpt.events.ModelError,
    chatgpt.events.ModelInterrupt,
    chatgpt.events.ModelGeneration,
):
    """Prints model events to the console."""

    def __init__(self):
        self.console = rich.console.Console()
        self.streaming = False

    async def on_model_start(self, model, context, tools):
        self.streaming = model.streaming
        rich.print(f"[magenta]Model:[/] {model.model_name}")
        rich.print(f"[magenta]Tools:[/] {', '.join(t.name for t in tools)}")
        for message in context:
            rich.print(message.serialize())

    async def on_model_generation(self, packet):
        if not self.streaming:
            return
        print(packet.content, end="", flush=True)
        if isinstance(packet, chatgpt.core.ToolUsage):
            print(packet.tool_name, end="", flush=True)
            print(packet.args_str, end="", flush=True)

    async def on_tool_use(self, usage):
        if self.streaming:
            return
        rich.print(usage.serialize())

    async def on_tool_result(self, results):
        rich.print(results.serialize())

    async def on_model_reply(self, reply):
        if self.streaming:
            return
        rich.print(reply.serialize())

    async def on_model_error(self, _):
        rich.print("\n[bold red]Model error:[/]")
        self.console.print_exception(show_locals=True)

    async def on_model_interrupt(self):
        rich.print("\n[bold red]Model interrupted...[/]")


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


class Calculator(chatgpt.tools.Tool):
    """A tool for solving math problems."""

    def __init__(self):
        self.name = "calculator"
        self.description = (
            "Answer math questions. Useful for solving math problems."
        )

        self.parameters = [
            chatgpt.tools.ToolParameter(
                type="string",
                name="expression",
                description="A valid numerical expression.",
            ),
        ]

    async def _run(self, expression: str) -> str:
        model = OpenAI(openai_api_key=OPENAI_API_KEY)  # type: ignore
        return await LLMMathChain.from_llm(model).arun(expression)


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
