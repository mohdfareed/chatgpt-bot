"""OpenAI chat model implementation."""

import asyncio

import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.tools
import chatgpt.utils


class ChatModel:
    """Class responsible for interacting with the OpenAI API."""

    def __init__(
        self,
        model: chatgpt.core.ModelConfig,
        memory: chatgpt.memory.ChatMemory,
        tools: list[chatgpt.tools.Tool] = [],
        handlers: list[chatgpt.events.ModelEvent] = [],
    ) -> None:
        self._generator: asyncio.Task | None = None
        self._metrics = chatgpt.events.MetricsHandler()
        handlers = handlers + [self._metrics]

        self.model = model
        """The model's configuration."""
        self.memory = memory
        """The memory of the model."""
        self.tools_manager = chatgpt.tools.ToolsManager(tools)
        """The manager of tools available to the model."""
        self.events_manager = chatgpt.events.EventsManager(handlers)
        """The events manager of callback handlers."""

    async def cancel(self):
        """Cancel the model's generation."""
        if self._generator is None:
            return
        self._generator.cancel()

    async def generate(self, message: chatgpt.core.UserMessage, stream=False):
        """Generate a response to a list of messages. None on error."""
        if self._generator is not None:
            raise chatgpt.core.ModelError("Model is already running")

        # add message to memory
        self.memory.chat_history.add_message(message)
        await self.events_manager.trigger_model_start(
            self.model,
            self.memory.messages,
            self.tools_manager.tools,
        )

        try:  # generate reply
            reply = None
            while not isinstance(reply, chatgpt.core.ModelReply):
                # generate reply
                reply = await self._request(stream)
                # store generated reply
                await self.events_manager.trigger_model_end(reply)
                reply.prompt_tokens = self._metrics.prompts_tokens
                reply.reply_tokens = self._metrics.generated_tokens
                reply.cost = self._metrics.cost
                self.memory.chat_history.add_message(reply)
                # use tool if necessary
                if type(reply) == chatgpt.core.ToolUsage:
                    await self._use_tool(reply)
        except Exception as e:
            await self.events_manager.trigger_model_error(e)
            raise chatgpt.core.ModelError("Failed to generate reply") from e

        # store reply
        await self.events_manager.trigger_model_reply(reply)
        self.memory.chat_history.add_message(reply)
        return reply

    async def _request(self, stream) -> chatgpt.core.ModelMessage:
        # request response from openai
        request = dict(self._params(), stream=stream)
        completion = await chatgpt.utils.completion(**request)  # type: ignore

        if not stream:  # process response if not streaming
            reply = chatgpt.utils.parse_completion(
                completion, self.model.model_name  # type: ignore
            )
            await self.events_manager.trigger_model_generation(reply)
        else:  # stream response, process as it comes in
            self._generator = asyncio.create_task(self._stream(completion))
            reply = await self._generator
        return reply

    async def _stream(self, completion):
        aggregator = _MessageAggregator()
        try:  # start a task to parse the completion packets
            async for packet in completion:  # type: ignore
                reply = chatgpt.utils.parse_completion(
                    packet, self.model.model_name
                )
                await self.events_manager.trigger_model_generation(reply)
                # aggregate messages into one
                aggregator.add(reply)
        except (asyncio.CancelledError, KeyboardInterrupt):  # canceled
            await self.events_manager.trigger_model_interrupt()
            aggregator.finish_reason = chatgpt.core.FinishReason.CANCELED
        return aggregator.reply

    async def _use_tool(self, usage: chatgpt.core.ToolUsage):
        # get tool results
        await self.events_manager.trigger_tool_use(usage)
        results = await self.tools_manager.use(usage)
        # store tool results
        await self.events_manager.trigger_tool_result(results)
        self.memory.chat_history.add_message(results)

    def _params(self):
        messages = [m.to_message_dict() for m in self.memory.messages]
        if self.model.prompt:
            messages.insert(0, self.model.prompt.to_message_dict())

        parameters = dict(
            messages=messages,
            functions=self.tools_manager.to_dict(),
            **self.model.params(),
        )
        return parameters


class _MessageAggregator:
    def __init__(self):
        self.content = ""
        self.tool_name = None
        self.args_str = None
        self.finish_reason = chatgpt.core.FinishReason.UNDEFINED

    def add(self, message: chatgpt.core.ModelMessage):
        self.content += message.content
        self.finish_reason = message.finish_reason
        if isinstance(message, chatgpt.core.ToolUsage):
            self.tool_name = (self.tool_name or "") + (message.tool_name or "")
            self.args_str = (
                ((self.args_str or "") + (message.args_str or ""))
                if self.args_str or message.args_str
                else None
            )

    @property
    def reply(self):
        if self.tool_name:
            reply = chatgpt.core.ToolUsage(self.tool_name, self.args_str)
        else:
            reply = chatgpt.core.ModelReply(self.content)
        reply.finish_reason = self.finish_reason
        return reply
