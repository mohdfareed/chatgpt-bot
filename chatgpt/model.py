"""OpenAI chat model implementation."""

from typing_extensions import override

import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.messages
import chatgpt.openai.chat_model
import chatgpt.tools


class ChatModel(chatgpt.openai.chat_model.OpenAIChatModel):
    """Class responsible for interacting with the OpenAI API."""

    def __init__(
        self,
        memory: chatgpt.memory.ChatMemory,
        handlers: list[chatgpt.events.ModelEvent] = [],
    ) -> None:
        super().__init__(handlers=handlers)
        self.memory = memory
        """The memory of the model."""

    @override
    async def run(self, new_message: chatgpt.messages.UserMessage):
        """Run the model."""
        # start running the model
        await self.events_manager.trigger_model_run(self)
        try:
            reply = await self._run_model(self._core(new_message))
        except chatgpt.core.ModelError:
            return  # model error, do nothing

        # broadcast reply if any
        if isinstance(reply, chatgpt.messages.ModelMessage):
            await self.events_manager.trigger_model_reply(reply)
        return reply

    async def _core(self, new_message: chatgpt.messages.UserMessage):
        # update model config, tools, and history
        self.config = await self.memory.history.model
        self.tools_manager = chatgpt.tools.ToolsManager(self.config.tools)
        await self.memory.history.add_message(new_message)

        reply = None
        while True:  # run until model has replied or is stopped
            # generate reply and add to memory
            reply = await self._generate_reply(await self.memory.messages)
            await self.memory.history.add_message(reply)
            if not self._running:
                break  # ensure model is still running

            # use tool if model is still running and has requested it
            if isinstance(reply, chatgpt.messages.ToolUsage):
                await self._use_tool(reply)

            # reply if the model generates a message content
            if reply.content:
                return reply

    async def _use_tool(self, usage: chatgpt.messages.ToolUsage):
        # use tool as cancelable task
        await self.events_manager.trigger_tool_use(usage)
        results = await self._cancelable(self.tools_manager.use(usage))
        # add to memory if not cancelled
        if isinstance(results, chatgpt.messages.ToolResult):
            await self.events_manager.trigger_tool_result(results)
            await self.memory.history.add_message(results)
        return results
