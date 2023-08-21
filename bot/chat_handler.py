"""Chat messages handler. Handles model generated replies and streams."""

import asyncio
import uuid

from typing_extensions import override

import bot
import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.messages
from bot import core, formatter, telegram_utils, tools

TOOL_USAGE_MESSAGE = """
Using tool: <code>{tool_name}</code>
With parameters:
<code>{args_str}</code>
{content}
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
    chatgpt.events.ToolUse,
    chatgpt.events.ToolResult,
    chatgpt.events.ModelError,
):
    """Handles model generated replies."""

    CHUNK_TIME = 1
    """The time to wait between sending chunks, in seconds."""
    running_models: dict[int, chatgpt.core.ChatModel] = {}
    """The list of running models."""

    def __init__(self, message: core.TelegramMessage, reply=False):
        self.model_id = int(uuid.uuid4())
        """The model's unique identifier."""
        self.user_message = message
        """The user message to which the model is replying."""
        self.is_replying = reply
        """Whether the model is replying to the message."""
        self.timer = Timer()
        """The timer to wait between sending chunks."""

    @override
    async def on_model_run(self, model):
        # set typing status
        self.typing = telegram_utils.set_typing_status(self.user_message)
        ModelMessageHandler.running_models[self.model_id] = model

    @override
    async def on_model_start(self, config, context, tools):
        # send first packet
        self.timer.count = self.CHUNK_TIME
        # reset handler states
        self.reply = None  # the model's reply message
        self.aggregated_reply = None  # the aggregated reply message
        self.status = [[]]  # message status (none initially)
        self.status += [[StopModel(self.model_id)]]  # the stop button

    @override
    async def on_model_generation(self, packet, aggregator):
        if not aggregator:  # not streaming
            return
        # store the aggregated reply
        self.aggregated_reply = aggregator.reply
        # wait for chunks to accumulate
        if self.timer.count < self.CHUNK_TIME:
            return

        # send packet
        await self._send_packet(aggregator.reply)
        self.timer.start()  # reset timer

    @override
    async def on_model_end(self, message):
        self.timer.stop()  # stop the timer
        await self._send_packet(message, final=True)  # send the final packet
        # check if the model has finished with a reply
        if not self.reply:
            bot.logger.error(f"Model's reply is empty.\n{message.serialize()}")
            raise chatgpt.core.ModelError("Model did not generate a reply.")

        # set the message's metadata with the sent reply's metadata
        message.id = str(self.reply.id)
        message.metadata = self.reply.metadata

    @override
    async def on_tool_use(self, usage):
        # store tool usage to append its results
        self.usage = usage
        # finalize the message
        await self._finalize_message_status(usage)
        await self._send_packet(usage, final=True)

    @override
    async def on_tool_result(self, results):
        if not self.reply:
            raise
        # append the results to the reply
        await self._send_packet(self.usage, results, final=True)

    @override
    async def on_model_reply(self, reply):
        # pop the model from the running models list
        ModelMessageHandler.running_models.pop(self.model_id)
        # finalize the message
        await self._finalize_message_status(reply)
        await self._send_packet(
            reply,
            final=reply.finish_reason
            is not chatgpt.core.FinishReason.CANCELLED,
        )

    @override
    async def on_model_error(self, error):
        # append the error to the message status
        if isinstance(error, chatgpt.core.ModelError):
            self.status += [[Status(str(error))]]

    async def _finalize_message_status(
        self, message: chatgpt.messages.ModelMessage
    ):
        self.status = [[]]  # reset status
        # set message status by resolving finish reason
        if message.finish_reason == chatgpt.core.FinishReason.UNDEFINED:
            self.status += [[Status("Model Finished Unexpectedly")]]
        if message.finish_reason == chatgpt.core.FinishReason.LIMIT_REACHED:
            self.status += [[Status("Size Limit Reached")]]
        if message.finish_reason == chatgpt.core.FinishReason.CENSORED:
            self.status += [[Status("Censored")]]
        if message.finish_reason == chatgpt.core.FinishReason.CANCELLED:
            self.status += [[Status("Cancelled")]]

    async def _send_packet(
        self,
        new_message: chatgpt.messages.ModelMessage,
        tool_results: chatgpt.messages.ToolResult | None = None,
        final=False,
    ):
        # parse message
        if not (message := _create_message(new_message, tool_results)):
            return
        # add ellipsis if still generating or no message
        if not final or not message:
            message += "..."

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


class StopModel(core.Button):
    """The button to stop a model."""

    def __init__(self, model_id: int):
        super().__init__(str(model_id), "Cancel")

    @override
    @classmethod
    async def callback(cls, data, query):
        """The callback for the button."""
        try:  # only if model is running
            model_id = int(data)
            ModelMessageHandler.running_models[model_id].stop()
            await query.answer("Model stopped")
        except KeyError:
            await query.answer("Model is not running")


class Status(core.Button):
    """Non-clickable button to show the model status."""

    def __init__(self, status: str):
        super().__init__("", status)

    @override
    @classmethod
    async def callback(cls, data, query):
        """The callback for the button."""
        # do nothing
        await query.answer()


class Timer:
    """Basic timer, accurate to 0.1 seconds."""

    def __init__(self):
        self.count: float
        """The number of seconds passed."""
        self._timer = None

    def start(self):
        """Start the timer."""
        self.stop()
        self.count = 0
        self._timer = asyncio.create_task(self._start_timer())

    def stop(self):
        """Stop the timer."""
        self._timer.cancel() if self._timer else None

    async def _start_timer(self):
        while True:
            self.count += 0.01
            await asyncio.sleep(0.01)


def _create_message(
    message: chatgpt.messages.ModelMessage, results=None
) -> str:
    if isinstance(message, chatgpt.messages.ToolUsage):
        return _format_tool_usage(message, results)
    return message.content


def _format_tool_usage(usage: chatgpt.messages.ToolUsage, results=None) -> str:
    if not results:
        return TOOL_USAGE_MESSAGE.format(
            tool_name=usage.tool_name,
            content=usage.content,
            args_str=usage.args_str,
        )

    # truncate results to 450 characters with ellipsis
    results = formatter.format_message(
        results.content[:450] + "..."
        if len(results.content) > 450
        else results.content
    )  # parse results

    tool = tools.from_tool_name(usage.tool_name)
    return TOOL_RESULTS_MESSAGE.format(
        tool_name=tool.title,
        args_str=usage.args_str,
        content=usage.content,
        results=results,
    )
