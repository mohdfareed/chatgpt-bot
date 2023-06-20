"""OpenAI chat model implementation."""

import asyncio

import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.openai
import chatgpt.tools


class ChatModel(chatgpt.openai.OpenAIModel):
    """Class responsible for interacting with the OpenAI API."""

    def __init__(
        self,
        model: chatgpt.core.ModelConfig,
        memory: chatgpt.memory.ChatMemory,
        tools: list[chatgpt.tools.Tool] = [],
        handlers: list[chatgpt.events.ModelEvent] = [],
    ) -> None:
        super().__init__(model, tools, handlers)
        self.memory = memory
        """The memory of the model."""

    async def run(self, new_message: chatgpt.core.UserMessage):
        """Generate a response to a new message."""
        await super().run([new_message])

    async def _run_model(self, input):
        new_message = input[0]
        await self.events_manager.trigger_model_run(new_message)
        self.memory.chat_history.add_message(new_message)
        reply = None

        while self._running:
            # generate reply and add to memory
            reply = await self._generate_reply(self.memory.messages)
            if not reply:
                break  # break if no reply generated
            self.memory.chat_history.add_message(reply)

            # use tool if needed
            if self._running and type(reply) == chatgpt.core.ToolUsage:
                results = await self._use_tool(reply)
                if results is not None:  # store results and continue
                    self.memory.chat_history.add_message(results)
                    continue
            break  # break when no tool results to return to model

        # trigger events and return reply
        if isinstance(reply, chatgpt.core.ModelMessage):
            await self.events_manager.trigger_model_reply(reply)
        return reply

    async def _use_tool(self, usage: chatgpt.core.ToolUsage):
        await self.events_manager.trigger_tool_use(usage)
        results = await self._cancelable(self.tools_manager.use(usage))
        if results is not None:
            await self.events_manager.trigger_tool_result(results)
        return results
