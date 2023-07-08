"""Addon implementations for ChatGPT."""

import rich
import rich.console
from langchain import LLMMathChain, OpenAI
from typing_extensions import override

import chatgpt.core
import chatgpt.events
import chatgpt.tools
from chatgpt import OPENAI_API_KEY


class ConsoleHandler(
    chatgpt.events.ModelRun,
    chatgpt.events.ModelStart,
    chatgpt.events.ModelGeneration,
    chatgpt.events.ModelEnd,
    chatgpt.events.ToolUse,
    chatgpt.events.ToolResult,
    chatgpt.events.ModelReply,
    chatgpt.events.ModelInterrupt,
    chatgpt.events.ModelError,
):
    """Prints model events to the console."""

    def __init__(self):
        self.console = rich.console.Console()
        self.streaming = False

    @override
    async def on_model_run(self, _):
        rich.print(f"[bold blue]STARTING...[/]")

    @override
    async def on_model_start(self, config, context, tools):
        self.streaming = config.streaming
        rich.print(f"[magenta]Model:[/] {config.model}")
        rich.print(f"[magenta]Tools:[/] {', '.join(t.name for t in tools)}")
        for message in context:
            rich.print(message.serialize())

    @override
    async def on_model_generation(self, packet, aggregator):
        if not self.streaming:
            return
        rich.print(packet.content, end="", flush=True)
        if isinstance(packet, chatgpt.core.ToolUsage):
            rich.print(packet.tool_name, end="", flush=True)
            rich.print(packet.args_str, end="", flush=True)

    @override
    async def on_model_end(self, message):
        pass

    @override
    async def on_tool_use(self, usage):
        if self.streaming:
            return
        rich.print(usage.serialize())

    @override
    async def on_tool_result(self, results):
        rich.print(results.serialize())

    @override
    async def on_model_reply(self, reply):
        if self.streaming:
            return
        rich.print(reply.serialize())

    @override
    async def on_model_error(self, _):
        rich.print("\n[bold red]Model error:[/]")
        self.console.print_exception(show_locals=True)

    @override
    async def on_model_interrupt(self):
        rich.print("\n[bold red]Model interrupted...[/]")


class Calculator(chatgpt.tools.Tool):
    """A tool for solving math problems."""

    def __init__(self):
        self.name = "calculator"
        self.description = (
            "Answer math questions. Useful for solving math problems."
        )

        self.parameters = [
            chatgpt.tools.ToolParameter(
                name="expression",
                type="string",
                description="A valid numerical expression.",
            ),
        ]

    @override
    async def _run(self, expression: str) -> str:
        model = OpenAI(openai_api_key=OPENAI_API_KEY)  # type: ignore
        return await LLMMathChain.from_llm(model).arun(expression)
