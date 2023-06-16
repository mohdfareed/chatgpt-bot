"""Events manager and callback handlers for chatgpt."""

import abc

from chatgpt import models, types


class CallbackHandler(abc.ABC):
    """Callback handler for model events."""

    def __init__(self) -> None:
        super().__init__()
        self.reply_only = True
        """Whether the handler is used only when the model is replying."""

    @abc.abstractmethod
    async def on_model_start(self, context: list[types.Message]):
        """Called when a model is starting."""
        pass  # first (repeats if alternate sixth triggered)

    @abc.abstractmethod
    async def on_generation_start(self, messages: list[dict[str, str]]):
        """Called when a model is starting generation."""
        pass  # second

    @abc.abstractmethod
    async def on_model_generation(self, token: str):
        """Called when a model generates a token."""
        pass  # third (repeats)

    @abc.abstractmethod
    async def on_generation_end(self, generation: str):
        """Called when a model ends generation."""
        pass  # fourth

    @abc.abstractmethod
    def on_model_exit(self, reply: models.ModelReply):
        """Called when a model exists generation."""
        pass  # fifth

    @abc.abstractmethod
    def on_tool_use(self, usage: models.ToolUsage):
        """Called when a model uses a tool."""
        pass  # alternate fifth (repeats)

    @abc.abstractmethod
    def on_tool_result(self, results: models.ToolResult):
        """Called when a tool returns a result."""
        pass  # sixth (if fifth triggered, repeats)

    @abc.abstractmethod
    def on_model_error(self, error: Exception | KeyboardInterrupt):
        """Called when a model generates an error."""
        pass

    @abc.abstractmethod
    def on_tool_error(self, error: Exception):
        """Called when a tool generates an error."""
        pass


class AsyncCallbackHandler(CallbackHandler, abc.ABC):
    """Async callback handler for model events."""

    @abc.abstractmethod
    async def on_model_start(self, context):
        pass

    @abc.abstractmethod
    async def on_generation_start(self, messages):
        pass

    @abc.abstractmethod
    async def on_model_generation(self, token):
        pass

    @abc.abstractmethod
    async def on_generation_end(self, generation):
        pass

    @abc.abstractmethod
    async def on_model_exit(self, reply):
        pass

    @abc.abstractmethod
    async def on_tool_use(self, usage):
        pass

    @abc.abstractmethod
    async def on_tool_result(self, results):
        pass

    @abc.abstractmethod
    async def on_model_error(self, error):
        pass

    @abc.abstractmethod
    async def on_tool_error(self, error):
        pass


class EventsManager:
    """Events manager for managing event handlers."""

    def __init__(self, handlers: list[CallbackHandler] = []):
        self.handlers = handlers
        """The list of callback handlers."""

    @property
    def reply_handlers(self) -> list[CallbackHandler]:
        """The list of reply-only callback handlers."""
        return [h for h in self.handlers if h.reply_only]

    async def trigger_model_start(self, messages: list[types.Message]):
        """Trigger the on_model_start event for all handlers."""
        for handler in self.handlers:
            await handler.on_model_start(messages)

    async def trigger_generation_start(self, messages: list[dict[str, str]]):
        """Trigger the on_generation_start event for all handlers."""
        for handler in self.handlers:
            await handler.on_generation_start(messages)

    async def trigger_model_generation(self, token: str):
        """Trigger the on_model_generation event for all handlers."""
        for handler in self.handlers:
            await handler.on_model_generation(token)

    async def trigger_generation_end(self, generation: str):
        """Trigger the on_generation_end event for all handlers."""
        for handler in self.handlers:
            await handler.on_generation_end(generation)

    def trigger_model_exit(self, reply: models.ModelReply):
        """Trigger the on_model_exit event for all handlers."""
        for handler in self.handlers:
            handler.on_model_exit(reply)

    def trigger_model_error(self, error: Exception | KeyboardInterrupt):
        """Trigger the on_model_error event for all handlers."""
        for handler in self.handlers:
            handler.on_model_error(error)

    def trigger_tool_use(self, usage: models.ToolUsage):
        """Trigger the on_tool_use event for all handlers."""
        for handler in self.handlers:
            handler.on_tool_use(usage)

    def trigger_tool_result(self, results: models.ToolResult):
        """Trigger the on_tool_result event for all handlers."""
        for handler in self.handlers:
            handler.on_tool_result(results)

    def trigger_tool_error(self, error: Exception):
        """Trigger the on_tool_error event for all handlers."""
        for handler in self.handlers:
            handler.on_tool_error(error)
