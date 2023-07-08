"""Chat messages handler. Handles model generated replies and streams."""

import telegram.constants
from typing_extensions import override

import bot.formatter as formatter
import bot.models
import bot.utils as utils
import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.model

PARSE_MODE = telegram.constants.ParseMode.HTML

TOOL_USAGE_MESSAGE = """
```
Using tool:
{tool_name}

With options:
{args_str}
```
""".strip()


class ModelMessageHandler(
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
    """Handles model generated replies."""

    CHUNK_SIZE = 10
    """The number of packets to send at once."""

    def __init__(self, message: bot.models.TelegramMessage, reply=False):
        self.user_message = message
        """The user message to which the model is replying."""
        self.is_replying = reply

    @override
    async def on_model_run(self, _):
        pass

    @override
    async def on_model_start(self, config, context, tools):
        # set typing status
        await self.user_message.telegram_message.chat.send_action("typing")
        # set handler states
        self.counter = 0  # the accumulated packets counter
        self.last_message = ""  # the last message sent
        self.reply = None  # the model's reply message

    @override
    async def on_model_generation(self, packet, aggregator):
        if not aggregator or not aggregator.reply:
            return  # don't send packets if none are available
        # wait for chunks to accumulate
        if self.counter < self.CHUNK_SIZE:
            self.counter += 1
            return  # don't send packets if the counter is not full

        # send packet
        await self._send_packet(aggregator.reply)
        self.counter = 0  # reset counter

    @override
    async def on_model_end(self, message):
        # send remaining packets
        await self._send_packet(message)
        if not self.reply:  # if no reply was received
            raise chatgpt.core.ModelError("No reply was generated by model")
        # set the usage's metadata
        message.id = str(self.reply.message_id)
        message.metadata = bot.models.TelegramMessage(self.reply).metadata

    @override
    async def on_tool_use(self, usage):
        await utils.count_usage(self.user_message, usage)

    @override
    async def on_tool_result(self, results):
        # send results as a reply to the model's reply
        await self.reply.reply_html(f"<code>{results.content}</code>")

    @override
    async def on_model_reply(self, reply):
        await utils.count_usage(self.user_message, reply)

    @override
    async def on_model_error(self, _):
        pass

    @override
    async def on_model_interrupt(self):
        pass

    async def _send_packet(self, new_message: chatgpt.core.ModelMessage):
        message = _create_message(new_message)  # parse message
        if message == self.last_message:
            return  # don't send empty packets

        # send new message if no reply has been sent yet
        if not self.reply:
            await self._reply(
                message, isinstance(new_message, chatgpt.core.ToolUsage)
            )
        else:  # edit the existing reply otherwise
            await self.reply.edit_text(message)
        # update last message
        self.last_message = message

    async def _reply(self, new_message: str, tool_usage=False):
        # send message without replying if using a tool or not replying
        if not self.is_replying or tool_usage:
            self.reply = (
                await self.user_message.chat.telegram_chat.send_message(
                    new_message, PARSE_MODE
                )
            )
        else:  # reply to the user otherwise
            self.reply = await self.user_message.telegram_message.reply_html(
                new_message
            )


def _create_message(message: chatgpt.core.ModelMessage) -> str:
    if isinstance(message, chatgpt.core.ToolUsage):
        return formatter.md_html(_format_tool_usage(message))
    return formatter.md_html(message.content)


def _format_tool_usage(usage: chatgpt.core.ToolUsage) -> str:
    return TOOL_USAGE_MESSAGE.format(
        tool_name=usage.tool_name, args_str=usage.args_str[:1000]
    )
