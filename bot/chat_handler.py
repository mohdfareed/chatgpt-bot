"""Chat messages handler. Handles model generated replies and streams."""

import telegram.constants
from typing_extensions import override

import bot
import bot.formatter as formatter
import bot.models
import bot.utils as utils
import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.model

PARSE_MODE = telegram.constants.ParseMode.HTML

TOOL_USAGE_MESSAGE = """
Using tool: <code>{tool_name}</code>
With parameters:
<code>{args_str}</code>
""".strip()

TOOL_RESULTS_MESSAGE = f"""
{TOOL_USAGE_MESSAGE}
Results:
<code>{{results}}</code>
""".strip()


class ModelMessageHandler(
    chatgpt.events.ModelStart,
    chatgpt.events.ModelGeneration,
    chatgpt.events.ModelEnd,
    chatgpt.events.ToolResult,
):
    """Handles model generated replies."""

    CHUNK_SIZE = 10
    """The number of packets to send at once."""

    def __init__(self, message: bot.models.TelegramMessage, reply=False):
        self.user_message = message
        """The user message to which the model is replying."""
        self.is_replying = reply

    @override
    async def on_model_start(self, config, context, tools):
        # set typing status
        await self.user_message.telegram_message.chat.send_action("typing")
        # set handler states
        self.counter = 0  # the accumulated packets counter
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
        # handle finish reason
        await self._handle_finish_reason(message.finish_reason)
        # send remaining packets
        await self._send_packet(message)
        # check if the model has finished with a reply
        if not self.reply:
            bot.logger.warning(
                "No reply was generated by model..." + message.serialize()
            )
            return

        # set the message's metadata with the sent reply's metadata
        message.id = str(self.reply.message_id)
        message.metadata = bot.models.TelegramMessage(self.reply).metadata
        # store tool usage to append its results
        if isinstance(message, chatgpt.core.ToolUsage):
            self.usage = message

    @override
    async def on_tool_result(self, results):
        # append the results to the reply
        await self._edit(_create_message(self.usage, results))

    async def _handle_finish_reason(self, reason: chatgpt.core.FinishReason):
        if reason == chatgpt.core.FinishReason.UNDEFINED:
            raise chatgpt.core.ModelError(
                "The model has finished unexpectedly."
            )
        if reason == chatgpt.core.FinishReason.FILTERED:
            await utils.reply_code(
                self.user_message, "The reply was filtered by the OpenAI."
            )
        if reason == chatgpt.core.FinishReason.LIMIT_REACHED:
            raise chatgpt.core.ModelError("The model has reached its limit.")
        if reason == chatgpt.core.FinishReason.CANCELLED:
            raise chatgpt.core.ModelError("The model has been cancelled.")

    async def _send_packet(self, new_message: chatgpt.core.ModelMessage):
        message = _create_message(new_message)  # parse message
        if self.reply:  # edit the existing reply
            await self._edit(message)
        else:  # send new message if no reply has been sent yet
            await self._reply(
                message, isinstance(new_message, chatgpt.core.ToolUsage)
            )

    async def _reply(self, new_message: str, tool_usage=False):
        if not new_message:  # don't send empty messages
            return
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

    async def _edit(self, new_message: str):
        try:  # try to edit the existing reply
            await self.reply.edit_text(new_message, PARSE_MODE)
        except Exception as e:
            if "Message is not modified" in str(e):
                return  # ignore if the message is not modified
            else:  # raise if the error is not due to the message not changing
                raise e


class ModelMetricsHandler(chatgpt.events.ToolUse, chatgpt.events.ModelReply):
    """Handles metrics of model generated replies."""

    def __init__(self, message: bot.models.TelegramMessage):
        self.user_message = message
        """The user message to which the model is replying."""

    @override
    async def on_tool_use(self, usage):
        # count usage towards the user's metrics
        await utils.count_usage(self.user_message, usage)

    @override
    async def on_model_reply(self, message):
        # count usage towards the user's metrics
        await utils.count_usage(self.user_message, message)


def _create_message(message: chatgpt.core.ModelMessage, results=None) -> str:
    if isinstance(message, chatgpt.core.ToolUsage):
        return formatter.md_html(_format_tool_usage(message, results))
    return formatter.md_html(message.content)


def _format_tool_usage(usage: chatgpt.core.ToolUsage, results=None) -> str:
    if not usage:
        return ""
    if not results:
        return TOOL_USAGE_MESSAGE.format(
            tool_name=usage.tool_name, args_str=usage.args_str
        )

    # truncate results to 450 characters with ellipsis
    results = formatter.md_html(
        results.content[:450] + "..."
        if len(results.content) > 450
        else results.content
    )  # parse results
    return TOOL_RESULTS_MESSAGE.format(
        tool_name=usage.tool_name,
        args_str=usage.args_str,
        results=results,
    )
