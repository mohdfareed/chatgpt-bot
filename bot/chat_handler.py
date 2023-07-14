"""Chat messages handler. Handles model generated replies and streams."""

import asyncio
import uuid

import telegram
from typing_extensions import override

import chatgpt.core
import chatgpt.events
import chatgpt.messages
from bot import core, formatter, telegram_utils

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
    chatgpt.events.ModelRun,
    chatgpt.events.ModelStart,
    chatgpt.events.ModelGeneration,
    chatgpt.events.ModelEnd,
    chatgpt.events.ModelReply,
    chatgpt.events.ToolResult,
):
    """Handles model generated replies."""

    CHUNK_SIZE = 10
    """The number of packets to send at once."""
    running_models: dict[int, chatgpt.core.ChatModel] = {}
    """The list of running models."""

    def __init__(self, message: core.TelegramMessage, reply=False):
        self.model_id = int(uuid.uuid4())
        """The model's unique identifier."""
        self.user_message = message
        """The user message to which the model is replying."""
        self.is_replying = reply
        """Whether the model is replying to the message."""

    @override
    async def on_model_run(self, model):
        ModelMessageHandler.running_models[self.model_id] = model

    @override
    async def on_model_start(self, config, context, tools):
        # set typing status
        self.typing = asyncio.create_task(
            telegram_utils.set_typing_status(self.user_message)
        )
        # reset handler states
        self.counter = 0  # the accumulated packets counter
        self.reply = None  # the model's reply message
        self.status = [[]]  # message status (none initially)
        self.status += [[StopModel(self.model_id)]]  # the stop button

    @override
    async def on_model_generation(self, packet, aggregator):
        if not aggregator:  # not streaming
            return

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
        self.status = []  # remove stop button
        self._resolve_finish_reason(message.finish_reason)
        await self._send_packet(message)
        # check if the model has finished with a reply
        if not self.reply:
            raise chatgpt.core.ModelError("Model did not generate a reply.")

        # set the message's metadata with the sent reply's metadata
        message.id = str(self.reply.id)
        message.metadata = self.reply.metadata
        # store tool usage to append its results
        if isinstance(message, chatgpt.messages.ToolUsage):
            self.usage = message

    @override
    async def on_tool_result(self, results):
        if not self.reply:
            raise
        # append the results to the reply
        await telegram_utils.edit_message(
            self.reply, _create_message(self.usage, results)
        )

    @override
    async def on_model_reply(self, reply):
        # pop the model from the running models list
        ModelMessageHandler.running_models.pop(self.model_id)

    async def _send_packet(self, new_message: chatgpt.messages.ModelMessage):
        message = _create_message(new_message)  # parse message
        if self.reply:  # edit the existing reply
            markup = telegram_utils.create_markup(self.status)
            await telegram_utils.edit_message(self.reply, message, markup)
        else:  # send new message if no reply has been sent yet
            await self._send_message(message)

    async def _send_message(self, new_message: str):
        if not new_message:  # don't send empty messages
            return
        self.typing.cancel() if self.typing else None  # stop typing

        status = telegram_utils.create_markup(self.status)
        if not self.is_replying:
            self.reply = await telegram_utils.send_message(
                self.user_message, new_message, status
            )
        else:  # reply to the user otherwise
            self.reply = await telegram_utils.reply(
                self.user_message, new_message, status
            )

    def _resolve_finish_reason(self, reason: chatgpt.core.FinishReason):
        if reason == chatgpt.core.FinishReason.UNDEFINED:
            self.status += [[Status("Model Finished Unexpectedly")]]
        if reason == chatgpt.core.FinishReason.LIMIT_REACHED:
            self.status += [[Status("Model Size Limit Reached")]]
        if reason == chatgpt.core.FinishReason.CENSORED:
            self.status += [[Status("Model was Censored")]]
        if reason == chatgpt.core.FinishReason.CANCELLED:
            self.status += [[Status("Model was Cancelled")]]


class StopModel(core.Button):
    """The button to stop a model."""

    def __init__(self, model_id: int):
        super().__init__(str(model_id), "Stop")

    @override
    @classmethod
    async def callback(cls, data, query):
        """The callback for the button."""
        try:  # only if model is running
            model_id = int(data)
            ModelMessageHandler.running_models[model_id].stop()
            await query.answer("Model Stopped")
        except (ValueError, KeyError):
            pass


class Status(core.Button):
    """Non-clickable button to show the model status."""

    def __init__(self, status: str):
        super().__init__("", status)

    @override
    @classmethod
    def callback(cls, data, query):
        """The callback for the button."""
        pass


def _create_message(
    message: chatgpt.messages.ModelMessage, results=None
) -> str:
    if isinstance(message, chatgpt.messages.ToolUsage):
        return _format_tool_usage(message, results)
    return message.content


def _format_tool_usage(usage: chatgpt.messages.ToolUsage, results=None) -> str:
    if not results:
        return TOOL_USAGE_MESSAGE.format(
            tool_name=usage.tool_name, args_str=usage.args_str
        )

    # truncate results to 450 characters with ellipsis
    results = formatter.format_message(
        results.content[:450] + "..."
        if len(results.content) > 450
        else results.content
    )  # parse results
    return TOOL_RESULTS_MESSAGE.format(
        tool_name=usage.tool_name,
        args_str=usage.args_str,
        results=results,
    )
