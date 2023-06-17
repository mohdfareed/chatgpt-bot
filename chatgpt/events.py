"""Events manager and callback handlers for chatgpt."""

import abc
import inspect

from chatgpt import core, logger, types, utils


class EventsManager:
    """Events manager for managing event handlers."""

    def __init__(self, handlers: list["CallbackHandler"] = []):
        self.handlers = handlers
        """The list of callback handlers."""

    @property
    def deep_handlers(self) -> list["CallbackHandler"]:
        """The list of none reply-only callback handlers."""
        return [h for h in self.handlers if not h.reply_only]

    async def trigger_model_start(self, messages: list[types.Message]):
        """Trigger the on_model_start event for all handlers."""
        for handler in self.handlers:
            await self._callback(handler.on_model_start, messages)

    async def trigger_model_generation(self, token: str):
        """Trigger the on_model_generation event for all handlers."""
        for handler in self.handlers:
            await self._callback(handler.on_model_generation, token)

    async def trigger_model_generation_end(self, message: core.ModelMessage):
        """Trigger the on_generation_end event for all handlers."""
        for handler in self.handlers:
            await self._callback(handler.on_model_end, message)

    async def trigger_model_exit(self, reply: core.ModelMessage):
        """Trigger the on_model_exit event for all handlers."""
        for handler in self.handlers:
            await self._callback(handler.on_model_reply, reply)

    async def trigger_tool_use(self, usage: core.ToolUsage):
        """Trigger the on_tool_use event for all handlers."""
        for handler in self.handlers:
            await self._callback(handler.on_tool_use, usage)

    async def trigger_tool_result(self, results: core.ToolResult):
        """Trigger the on_tool_result event for all handlers."""
        for handler in self.handlers:
            await self._callback(handler.on_tool_result, results)

    async def trigger_model_error(self, error: Exception | KeyboardInterrupt):
        """Trigger the on_model_error event for all handlers."""
        for handler in self.handlers:
            await self._callback(handler.on_model_error, error)

    async def _callback(self, method, *args, **kwargs):
        if inspect.iscoroutinefunction(method):
            return await method(*args, **kwargs)
        else:
            return method(*args, **kwargs)


class CallbackHandler(abc.ABC):
    """Callback handler for model events."""

    def __init__(self):
        self.reply_only = True
        """Whether the handler is used only when the model is replying."""

    def on_model_start(self, context: list[types.Message]):
        """Called when a model starts generation."""
        pass  # first

    def on_model_generation(self, token: str):
        """Called when a model generates a token."""
        pass  # second (repeats)

    def on_model_end(self, message: core.ModelMessage):
        """Called when a model ends generation."""
        pass  # third

    def on_tool_use(self, usage: core.ToolUsage):
        """Called when a model uses a tool."""
        pass  # fourth (if tool used)

    def on_tool_result(self, results: core.ToolResult):
        """Called when a tool returns a result."""
        pass  # fifth (if fourth triggered)

    def on_model_reply(self, reply: core.ModelMessage):
        """Called when a model replies and exists."""
        pass  # last

    def on_model_error(self, error: Exception | KeyboardInterrupt):
        """Called when a model generates an error."""
        pass


class AsyncCallbackHandler(CallbackHandler, abc.ABC):
    """Async callback handler for model events."""

    async def on_model_start(self, context: list[types.Message]):
        pass

    async def on_model_generation(self, token: str):
        pass

    async def on_model_end(self, message: core.ModelMessage):
        pass

    async def on_tool_use(self, usage: core.ToolUsage):
        pass

    async def on_tool_result(self, results: core.ToolResult):
        pass

    async def on_model_reply(self, reply: core.ModelMessage):
        pass

    async def on_model_error(self, error: Exception | KeyboardInterrupt):
        pass


class MetricsHandler(AsyncCallbackHandler):
    """Calculates request metrics."""

    def __init__(self, model: types.SupportedModel):
        super().__init__()
        self._prompts: list[dict[str, str]] = []
        self.reply_only = False

        self.model = model
        """The model used for reply generation."""
        self.prompts_tokens = 0
        """The total number of tokens in all prompts."""
        self.generated_tokens = 0
        """The total number of tokens in all generations."""

    async def on_model_start(self, context):
        # track all prompts
        self._prompts += [m.to_message_dict() for m in context]

    async def on_model_end(self, message):
        # calculate tokens for all generations
        self.prompts_tokens += utils.messages_tokens(self._prompts, self.model)
        if type(message) == core.ToolUsage:
            generated_text = message.tool_name + (message.args_str or "")
            self.generated_tokens += utils.tokens(generated_text, self.model)
        else:
            self.generated_tokens += utils.tokens(message.content, self.model)

        # if reply includes usage, compare to computed usage
        if message.prompt_tokens or message.reply_tokens:
            if message.prompt_tokens != self.prompts_tokens:
                logger.warning(
                    "Prompt tokens mismatch: {actual: %s, computed: %s}",
                    message.prompt_tokens,
                    self.prompts_tokens,
                )
            if message.reply_tokens != self.generated_tokens:
                logger.warning(
                    "Reply tokens mismatch: {actual: %s, computed: %s}",
                    message.reply_tokens,
                    self.generated_tokens,
                )


class ConsoleHandler(AsyncCallbackHandler):
    """Prints model events to the console."""

    def __init__(self, model: types.SupportedModel):
        super().__init__()
        self.reply_only = False
        self.model = model
        """The model used for reply generation."""

    async def on_model_start(self, context):
        from rich import print

        print("[bold]History[/]\n")
        for message in context:
            self._print_message(message)
        print()

    async def on_model_generation(self, token):
        from rich import print

        print(token, end="")

    async def on_tool_use(self, usage):
        from rich import print

        print(f"[bold]Using tool:[/] {usage.serialize()}")

    async def on_tool_result(self, results):
        from rich import print

        print(f"[bold]Tool result:[/] {results.serialize()}")

    async def on_model_reply(self, reply):
        from rich import print

        print(f"[bold green]Model returned:[/] {reply.serialize()}")

    async def on_model_error(self, _):
        from rich import print
        from rich.console import Console

        print("[bold red]Model error:[/]")
        Console().print_exception(show_locals=True)

    def _print_message(self, message: types.Message):
        from rich import print

        if type(message) == core.UserMessage:
            print(f"[blue]{message.name or 'You'}:[/] {message.content}")
        if type(message) == core.SystemMessage:
            print(f"SYSTEM: {message.content}")
        if type(message) == core.ToolResult:
            print(f"[cyan]{message.name}:[/] {message.content}")
        if type(message) == core.ModelMessage:
            print(f"[green]ChatGPT:[/] {message.content}")
        if type(message) == core.ToolUsage:
            print(
                f"[green]ChatGPT:[/] "
                f"[magenta]{message.tool_name}{message.arguments}[/]"
            )
