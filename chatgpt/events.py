"""Events manager and callback handlers for chatgpt."""

import abc
import inspect
import json
import typing

import chatgpt.core
import chatgpt.tools
import chatgpt.utils


class classproperty(property):
    def __get__(self, _, owner):
        return self.fget.__get__(None, owner)()


class EventsManager:
    """Events manager for managing event handlers."""

    def __init__(self, handlers: list["ModelEvent"] = []):
        self.handlers = handlers
        """The list of callback handlers."""

    async def trigger_model_start(
        self,
        model: chatgpt.core.ModelConfig,
        context: list[chatgpt.core.Message],
        tools: list[chatgpt.tools.Tool],
    ):
        """Trigger the on_model_start event for all handlers."""
        await self._trigger(ModelStart, model, context, tools)

    async def trigger_model_generation(self, token: str):
        """Trigger the on_model_generation event for all handlers."""
        await self._trigger(ModelGeneration, token)

    async def trigger_model_end(self, message: chatgpt.core.ModelMessage):
        """Trigger the on_model_end event for all handlers."""
        await self._trigger(ModelEnd, message)

    async def trigger_tool_use(self, usage: chatgpt.core.ToolUsage):
        """Trigger the on_tool_use event for all handlers."""
        await self._trigger(ToolUse, usage)

    async def trigger_tool_result(self, results: chatgpt.core.ToolResult):
        """Trigger the on_tool_result event for all handlers."""
        await self._trigger(ToolResult, results)

    async def trigger_model_reply(self, reply: chatgpt.core.ModelMessage):
        """Trigger the on_model_reply event for all handlers."""
        await self._trigger(ModelReply, reply)

    async def trigger_model_error(self, error: Exception):
        """Trigger the on_model_error event for all handlers."""
        await self._trigger(ModelError, error)

    async def trigger_model_interrupt(self, error: KeyboardInterrupt):
        """Trigger the on_model_interrupt event for all handlers."""
        await self._trigger(ModelInterrupt, error)

    async def _trigger(
        self, event: typing.Type["ModelEvent"], *args, **kwargs
    ):
        for handler in self.handlers:
            if not isinstance(handler, event):
                continue  # find handlers for the event
            # trigger the event callback on the handler
            await event.trigger(handler, *args, **kwargs)


class ModelEvent(abc.ABC):
    """Base class for all model events."""

    @classmethod
    async def trigger(cls, handler, *args: typing.Any, **kwargs: typing.Any):
        """Trigger the event callback."""
        if not isinstance(handler, cls):
            raise TypeError(
                f"Cannot trigger event '{cls}' on handler of: {type(handler)}"
            )

        callback: typing.Callable = getattr(handler, cls.callback().__name__)
        if inspect.iscoroutinefunction(callback):
            return await callback(*args, **kwargs)
        return callback(*args, **kwargs)

    @classmethod
    @abc.abstractmethod
    def callback(cls) -> typing.Callable[[typing.Any], typing.Any]:
        """The callback function for the event."""


class ModelStart(ModelEvent, abc.ABC):
    """Callback handler for model start events."""

    @abc.abstractmethod
    def on_model_start(
        self,
        model: chatgpt.core.ModelConfig,
        context: list[chatgpt.core.Message],
        tools: list[chatgpt.tools.Tool],
    ):
        """Called when a model starts generation."""

    @classmethod
    def callback(cls):
        return cls.on_model_start


class ModelGeneration(ModelEvent, abc.ABC):
    """Callback handler for model generation events."""

    @abc.abstractmethod
    def on_model_generation(self, token: str):
        """Called when a model generates a token."""

    @classmethod
    def callback(cls):
        return cls.on_model_generation


class ModelEnd(ModelEvent, abc.ABC):
    """Callback handler for model end events."""

    @abc.abstractmethod
    def on_model_end(self, message: chatgpt.core.ModelMessage):
        """Called when a model ends generation."""

    @classmethod
    def callback(cls):
        return cls.on_model_end


class ToolUse(ModelEvent, abc.ABC):
    """Callback handler for tool use events."""

    @abc.abstractmethod
    def on_tool_use(self, usage: chatgpt.core.ToolUsage):
        """Called when a model uses a tool."""

    @classmethod
    def callback(cls):
        return cls.on_tool_use


class ToolResult(ModelEvent, abc.ABC):
    """Callback handler for tool result events."""

    @abc.abstractmethod
    def on_tool_result(self, results: chatgpt.core.ToolResult):
        """Called when a tool returns a result."""

    @classmethod
    def callback(cls):
        return cls.on_tool_result


class ModelReply(ModelEvent, abc.ABC):
    """Callback handler for model reply events."""

    @abc.abstractmethod
    def on_model_reply(self, reply: chatgpt.core.ModelMessage):
        """Called when a model replies and exists."""

    @classmethod
    def callback(cls):
        return cls.on_model_reply


class ModelError(ModelEvent, abc.ABC):
    """Callback handler for model error events."""

    @abc.abstractmethod
    def on_model_error(self, error: Exception):
        """Called when a model generates an error."""

    @classmethod
    def callback(cls):
        return cls.on_model_error


class ModelInterrupt(ModelEvent, abc.ABC):
    """Callback handler for model interrupt events."""

    @abc.abstractmethod
    def on_model_interrupt(self, error: KeyboardInterrupt):
        """Called when a model is interrupted."""
        # TODO: add better event arguments

    @classmethod
    def callback(cls):
        return cls.on_model_interrupt


class MetricsHandler(ModelStart, ModelEnd):
    """Calculates request metrics."""

    def __init__(self):
        super().__init__()
        self._prompts: list[dict[str, str]] = []

        self.prompts_tokens = 0
        """The total number of tokens in all prompts."""
        self.generated_tokens = 0
        """The total number of tokens in all generations."""

    async def on_model_start(self, model, context, tools):
        # track all prompts
        self._prompts += [m.to_message_dict() for m in context]
        self._prompts += [
            {"functions": json.dumps(t.to_dict())} for t in tools
        ]
        self._model = model.model_name

    async def on_model_end(self, message):
        if not self._model:
            return

        # calculate prompts tokens
        self.prompts_tokens += chatgpt.utils.messages_tokens(
            self._prompts, self._model
        )
        # calculate generated tokens
        if type(message) == chatgpt.core.ToolUsage:
            generated_text = message.tool_name + (message.args_str or "")
            self.generated_tokens += chatgpt.utils.tokens(
                generated_text, self._model
            )
        else:
            self.generated_tokens += chatgpt.utils.tokens(
                message.content, self._model
            )

        # if reply includes usage, compare to computed usage
        if message.prompt_tokens or message.reply_tokens:
            if message.prompt_tokens != self.prompts_tokens:
                chatgpt.logger.warning(
                    "Prompt tokens mismatch: {actual: %s, computed: %s}",
                    message.prompt_tokens,
                    self.prompts_tokens,
                )
            if message.reply_tokens != self.generated_tokens:
                chatgpt.logger.warning(
                    "Reply tokens mismatch: {actual: %s, computed: %s}",
                    message.reply_tokens,
                    self.generated_tokens,
                )


class ConsoleHandler(
    ModelStart, ToolUse, ToolResult, ModelReply, ModelError, ModelInterrupt
):
    """Prints model events to the console."""

    async def on_model_start(self, model, context, tools):
        import rich

        rich.print(f"[bold]Model:[/] {model.model_name}")
        rich.print(f"[bold]Tools:[/] {', '.join(t.name for t in tools)}")

        rich.print("[bold]History[/]\n")
        for message in context:
            self._print_message(message)
        rich.print()

    async def on_tool_use(self, usage):
        import rich

        rich.print(f"[bold]Using tool:[/] {usage.serialize()}")
        rich.print()

    async def on_tool_result(self, results):
        import rich

        rich.print(f"[bold]Tool result:[/] {results.serialize()}")
        rich.print()

    async def on_model_reply(self, reply):
        import rich

        rich.print(f"[bold green]Model's reply:[/] {reply.serialize()}")
        rich.print()

    async def on_model_error(self, _):
        import rich
        from rich.console import Console

        rich.print("[bold red]Model error:[/]")
        Console().print_exception(show_locals=True)

    async def on_model_interrupt(self, _):
        import rich

        rich.print("[bold red]Model interrupted...[/]")

    def _print_message(self, message: chatgpt.core.Message):
        import rich

        if type(message) == chatgpt.core.UserMessage:
            rich.print(f"[blue]{message.name or 'You'}:[/] {message.content}")
        if type(message) == chatgpt.core.SystemMessage:
            rich.print(f"SYSTEM: {message.content}")
        if type(message) == chatgpt.core.ToolResult:
            rich.print(f"[bright_black]{message.name}:[/] {message.content}")
        if type(message) == chatgpt.core.ModelMessage:
            rich.print(f"[green]ChatGPT:[/] {message.content}")
        if type(message) == chatgpt.core.ToolUsage:
            rich.print(
                f"[green]ChatGPT:[/] "
                f"[magenta]{message.tool_name}{message.arguments}[/]"
            )
