"""OpenAI chat model implementation."""

import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.openai.chat_model
import chatgpt.tools

INSTRUCTIONS = """\
You may only use the following markdown in your replies:
*bold* _italic_ ~strikethrough~ __underline__ ||spoiler|| \
[inline URL](http://www.example.com/) `monospaced` @mentions #hashtags
```code blocks (without language)```
NEVER INCLUDE THE MESSAGE METADATA IN YOUR REPLIES"""
"""The core message included at the end of all system messages."""


class ChatModel(chatgpt.openai.chat_model.OpenAIChatModel):
    """Class responsible for interacting with the OpenAI API."""

    def __init__(
        self,
        memory: chatgpt.memory.ChatMemory,
        tools: list[chatgpt.tools.Tool] = [],
        handlers: list[chatgpt.events.ModelEvent] = [],
    ) -> None:
        super().__init__(tools=tools, handlers=handlers)
        self.memory = memory
        """The memory of the model."""

    async def run(self, new_message: chatgpt.core.UserMessage):
        """Run the model."""
        # start running the model
        await self.events_manager.trigger_model_run(new_message)
        reply = await self._run_model(self._core(new_message))
        # broadcast reply if any
        if isinstance(reply, chatgpt.core.ModelMessage):
            await self.events_manager.trigger_model_reply(reply)
        return reply

    async def _core(self, new_message: chatgpt.core.UserMessage):
        await self.memory.history.add_message(new_message)
        self.config = await self.memory.history.model  # update model config
        reply = None

        while True:  # run until model has replied or is stopped
            # retrieve history and add core instructions
            history = await self.memory.messages
            history.append(chatgpt.core.SystemMessage(INSTRUCTIONS))
            # generate reply and add to memory
            reply = await self._generate_reply(history)
            if reply is not None:  # potentially partial reply was generated
                await self.memory.history.add_message(reply)

            # use tool if model is still running and has requested it
            if isinstance(reply, chatgpt.core.ToolUsage) and self._running:
                await self._use_tool(reply)
                continue  # send results to model
            break  # no tool used or model stopped
        return reply

    async def _use_tool(self, usage: chatgpt.core.ToolUsage):
        # use tool as cancelable task
        await self.events_manager.trigger_tool_use(usage)
        results = await self._cancelable(self.tools_manager.use(usage))
        # add to memory if not cancelled
        if isinstance(results, chatgpt.core.ToolResult):
            await self.events_manager.trigger_tool_result(results)
            await self.memory.history.add_message(results)
        return results
