"""OpenAI chat model implementation."""

import asyncio
import json

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
        self._running = False
        self._generator: asyncio.Task | None = None
        self._metrics = _MetricsHandler()
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
        interrupted = False
        if self._generator is not None:
            self._generator.cancel()
            interrupted = True
        if self._running:
            self._running = False
            interrupted = True

        if interrupted:  # trigger interrupt event
            await self.events_manager.trigger_model_interrupt()

    async def start(self, message: chatgpt.core.UserMessage):
        """Generate a response to a list of messages. None on error."""
        if self._running or self._generator is not None:
            raise chatgpt.core.ModelError("Model is already running")

        # add message to memory
        self.memory.chat_history.add_message(message)
        try:  # generate reply
            reply = await self._run()
        except Exception as e:
            await self.events_manager.trigger_model_error(e)
            self._generator = None
            self._running = False
            raise chatgpt.core.ModelError("Failed to generate reply") from e
        return reply

    async def _run(self):
        reply = None
        self._running = True

        while self._running:
            params = (
                self.model,
                self.memory.messages,
                self.tools_manager.tools,
            )

            # generate reply
            await self.events_manager.trigger_model_start(*params)
            reply = await self._generate()
            await self.events_manager.trigger_model_end(reply)
            # fix reply metrics and add to memory
            reply.prompt_tokens = self._metrics.prompts_tokens
            reply.reply_tokens = self._metrics.generated_tokens
            reply.cost = self._metrics.cost
            self.memory.chat_history.add_message(reply)
            # use tool if needed
            if self._running and type(reply) == chatgpt.core.ToolUsage:
                results = await self._use_tool(reply)
                if results is not None:  # store results and continue
                    self.memory.chat_history.add_message(results)
                    continue  # REVIEW: maybe continue even if no results?
            break

        self._running = False
        if isinstance(reply, chatgpt.core.ModelMessage):
            await self.events_manager.trigger_model_reply(reply)
        return reply

    async def _generate(self) -> chatgpt.core.ModelMessage:
        # request response from openai
        request = dict(self._params())
        completion = await chatgpt.utils.completion(**request)  # type: ignore

        if self.model.streaming:  # stream response, process as it comes in
            self._generator = asyncio.create_task(self._stream(completion))
            reply = await self._generator
            self._generator = None
        else:  # process response if not streaming
            reply = chatgpt.utils.parse_completion(
                completion, self.model.model_name  # type: ignore
            )
            await self.events_manager.trigger_model_generation(reply)

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
            aggregator.finish_reason = chatgpt.core.FinishReason.CANCELLED
        return aggregator.reply

    async def _use_tool(self, usage: chatgpt.core.ToolUsage):
        await self.events_manager.trigger_tool_use(usage)
        self._generator = asyncio.create_task(self.tools_manager.use(usage))
        results = await self._generator
        self._generator = None

        if results is not None:
            await self.events_manager.trigger_tool_result(results)
        return results

    def _params(self):
        messages = [m.to_message_dict() for m in self.memory.messages]
        if self.model.prompt:
            messages.insert(0, self.model.prompt.to_message_dict())

        parameters = dict(
            messages=messages,
            functions=self.tools_manager.to_dict(),
            **self.model.params(),
        )
        return {k: v for k, v in parameters.items() if v is not None}

    def _is_replying(self, reply):
        return isinstance(reply, chatgpt.core.ModelMessage) and reply.content


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
            self.tool_name = (self.tool_name or "") + message.tool_name
            self.args_str = (self.args_str or "") + message.args_str

    @property
    def reply(self):
        if self.tool_name and self.args_str:
            reply = chatgpt.core.ToolUsage(self.tool_name, self.args_str)
            reply.content = self.content
        elif self.tool_name or self.args_str:
            raise chatgpt.core.ModelError("Invalid tool usage received")
        else:
            reply = chatgpt.core.ModelMessage(self.content)
        reply.finish_reason = self.finish_reason
        return reply


class _MetricsHandler(chatgpt.events.ModelStart, chatgpt.events.ModelEnd):
    """Calculates request metrics as the model is used."""

    def __init__(self):
        super().__init__()
        self.prompts_tokens: int
        """The total number of tokens in all prompts."""
        self.generated_tokens: int
        """The total number of tokens in all generations."""
        self.tools_tokens: int
        """The total number of tokens taken by tools declarations."""
        self.cost: float
        """The total cost of all generations."""

    async def on_model_start(self, model, context, tools):
        self._model = model.model_name
        self._prompts = context
        self._tools = tools
        # reset metrics
        self.prompts_tokens = 0
        self.generated_tokens = 0
        self.tools_tokens = 0
        self.cost = 0.0
        self.has_tools = len(tools) > 0

    async def on_model_end(self, message):
        if not self._model:
            return

        # compute prompt tokens count
        self.prompts_tokens = chatgpt.utils.messages_tokens(
            self._prompts, self._model
        )
        # compute generated tokens count
        self.generated_tokens = chatgpt.utils.model_tokens(
            message, self._model, self.has_tools
        )
        # compute tools tokens count
        self.tools_tokens = chatgpt.utils.tools_tokens(
            self._tools, self._model
        )
        # compute cost
        self.cost = chatgpt.utils.tokens_cost(
            self.prompts_tokens, self._model, is_reply=False
        ) + chatgpt.utils.tokens_cost(
            self.generated_tokens, self._model, is_reply=True
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
