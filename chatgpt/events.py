"""Events manager and callback handlers for chatgpt."""

import abc
import inspect
import typing

import chatgpt.core
import chatgpt.messages
import chatgpt.tools


class EventsManager:
    """Manager of callback handlers for a model's events."""

    from chatgpt.openai.aggregator import MessageAggregator

    def __init__(self, handlers: list["ModelEvent"] = []):
        self.handlers = handlers
        """The list of callback handlers."""

    def add_handler(self, handler: "ModelEvent"):
        """Add a callback handler."""
        self.handlers.append(handler)

    def remove_handler(self, handler: "ModelEvent"):
        """Remove a callback handler."""
        self.handlers.remove(handler)

    async def trigger_model_run(self, model: chatgpt.core.ChatModel):
        """Trigger the on_model_run event for all handlers."""
        await self._trigger(ModelRun, model)

    async def trigger_model_start(
        self,
        config: chatgpt.core.ModelConfig,
        context: list[chatgpt.messages.Message],
        tools: list[chatgpt.tools.Tool],
    ):
        """Trigger the on_model_start event for all handlers."""
        await self._trigger(ModelStart, config, context, tools)

    async def trigger_model_generation(
        self,
        packet: chatgpt.messages.ModelMessage,
        aggregator: MessageAggregator | None,
    ):
        """Trigger the on_model_generation event for all handlers."""
        await self._trigger(ModelGeneration, packet, aggregator)

    async def trigger_model_end(self, message: chatgpt.messages.ModelMessage):
        """Trigger the on_model_end event for all handlers."""
        await self._trigger(ModelEnd, message)

    async def trigger_tool_use(self, usage: chatgpt.messages.ToolUsage):
        """Trigger the on_tool_use event for all handlers."""
        await self._trigger(ToolUse, usage)

    async def trigger_tool_result(self, results: chatgpt.messages.ToolResult):
        """Trigger the on_tool_result event for all handlers."""
        await self._trigger(ToolResult, results)

    async def trigger_model_reply(self, reply: chatgpt.messages.ModelMessage):
        """Trigger the on_model_reply event for all handlers."""
        await self._trigger(ModelReply, reply)

    async def trigger_model_error(self, error: Exception):
        """Trigger the on_model_error event for all handlers."""
        await self._trigger(ModelError, error)

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


class ModelRun(ModelEvent, abc.ABC):
    """Event triggered when model starts running."""

    @abc.abstractmethod
    def on_model_run(self, model: chatgpt.core.ChatModel):
        """Called when a model starts running."""

    @classmethod
    def callback(cls):
        return cls.on_model_run


class ModelStart(ModelEvent, abc.ABC):
    """Event triggered before model starts generating tokens."""

    @abc.abstractmethod
    def on_model_start(
        self,
        config: chatgpt.core.ModelConfig,
        context: list[chatgpt.messages.Message],
        tools: list[chatgpt.tools.Tool],
    ):
        """Called before a model starts generating tokens."""

    @classmethod
    def callback(cls):
        return cls.on_model_start


class ModelGeneration(ModelEvent, abc.ABC):
    """Event triggered on model generating a token."""

    from chatgpt.openai.aggregator import MessageAggregator

    @abc.abstractmethod
    def on_model_generation(
        self,
        packet: chatgpt.messages.ModelMessage,
        aggregator: MessageAggregator | None,
    ):
        """Called when a model generates a token."""

    @classmethod
    def callback(cls):
        return cls.on_model_generation


class ModelEnd(ModelEvent, abc.ABC):
    """Event triggered on model ending generation."""

    @abc.abstractmethod
    def on_model_end(self, message: chatgpt.messages.ModelMessage):
        """Called when a model finishes generating tokens."""

    @classmethod
    def callback(cls):
        return cls.on_model_end


class ToolUse(ModelEvent, abc.ABC):
    """Event triggered on model using a tool."""

    @abc.abstractmethod
    def on_tool_use(self, usage: chatgpt.messages.ToolUsage):
        """Called when a model uses a tool."""

    @classmethod
    def callback(cls):
        return cls.on_tool_use


class ToolResult(ModelEvent, abc.ABC):
    """Event triggered on tool returning a result to model."""

    @abc.abstractmethod
    def on_tool_result(self, results: chatgpt.messages.ToolResult):
        """Called when a tool returns a result to the model."""

    @classmethod
    def callback(cls):
        return cls.on_tool_result


class ModelReply(ModelEvent, abc.ABC):
    """Event triggered on model replying to the user."""

    @abc.abstractmethod
    def on_model_reply(self, reply: chatgpt.messages.ModelMessage):
        """Called when a model replies and exists."""

    @classmethod
    def callback(cls):
        return cls.on_model_reply


class ModelError(ModelEvent, abc.ABC):
    """Event triggered on model encountering an error."""

    @abc.abstractmethod
    def on_model_error(self, error: Exception):
        """Called when a model encounters an error."""

    @classmethod
    def callback(cls):
        return cls.on_model_error
