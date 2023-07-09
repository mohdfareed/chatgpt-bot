"""OpenAI API models interface."""

import asyncio
import typing

import chatgpt.core
import chatgpt.events
import chatgpt.openai.tokenization
import chatgpt.tools
from chatgpt.openai import utils
from chatgpt.openai.aggregator import MessageAggregator
from chatgpt.openai.metrics import MetricsHandler

T = typing.TypeVar("T")


class OpenAIChatModel:
    """Class responsible for interacting with the OpenAI API."""

    def __init__(
        self,
        config: chatgpt.core.ModelConfig = chatgpt.core.ModelConfig(),
        handlers: list[chatgpt.events.ModelEvent] = [],
    ) -> None:
        self._running = False
        self._model_task: asyncio.Task | None = None
        self._metrics = MetricsHandler()
        handlers = handlers + [self._metrics]

        self.config = config
        """The model's configuration."""
        self.tools_manager = chatgpt.tools.ToolsManager(config.tools)
        """The manager of tools available to the model."""
        self.events_manager = chatgpt.events.EventsManager(handlers)
        """The events manager of callback handlers."""

    async def stop(self):
        """Stop the model from running."""
        interrupted = False
        if self._model_task is not None:
            self._model_task.cancel()
            interrupted = True
        if self._running:
            self._running = False
            interrupted = True

        if interrupted:  # trigger interrupt event
            await self.events_manager.trigger_model_interrupt()

    async def run(self, messages: list[chatgpt.core.Message]):
        """Run the model."""
        # example implementation of the model's run method
        # it is responsible for triggering the run and reply events, defining
        # the model's inputs and outputs, and providing the core logic

        # broadcast input and start running the model
        await self.events_manager.trigger_model_run(messages)
        reply = await self._run_model(self._core_logic(messages))
        # broadcast reply if any
        if isinstance(reply, chatgpt.core.ModelMessage):
            await self.events_manager.trigger_model_reply(reply)
        return reply

    async def _core_logic(self, messages: list[chatgpt.core.Message]):
        # example implementation of the model's core logic
        # the core logic relies mainly on the generate_reply method to trigger
        # the model to generate a reply
        return await self._generate_reply(messages)

    async def _run_model(
        self, core_logic: typing.Coroutine[typing.Any, typing.Any, T]
    ) -> T:
        if self._running or self._model_task is not None:
            raise chatgpt.core.ModelError("Model is already running")

        try:  # generate reply
            self._running = True
            reply = await core_logic
        except chatgpt.core.ModelError as e:
            await self.events_manager.trigger_model_error(e)
            raise  #  propagate model errors
        except Exception as e:  # handle errors
            await self.events_manager.trigger_model_error(e)
            raise chatgpt.core.ModelError("Failed to generate a reply") from e
        finally:  # cleanup
            self._model_task = None
            self._running = False
        return reply

    async def _generate_reply(self, messages: list[chatgpt.core.Message]):
        # generate a reply to a list of messages
        params = (self.config, messages, self.tools_manager.tools)
        await self.events_manager.trigger_model_start(*params)
        reply = await self._request_completion(*params)

        # trigger model end event if model was not canceled
        if not isinstance(reply, chatgpt.core.ModelMessage):
            return None  # canceled
        await self.events_manager.trigger_model_end(reply)
        return reply

    async def _request_completion(self, *params):
        # request response from openai
        request = utils.create_completion_params(*params)
        completion = await self._cancelable(
            utils.generate_completion(**request)
        )
        if completion is None:  # canceled
            return completion

        # return streamed response if streaming
        if self.config.streaming:  # triggers model generation events
            return await self._cancelable(self._stream_completion(completion))  # type: ignore

        # return processed response if not streaming
        reply = _parse_completion(completion, self.config.chat_model)  # type: ignore
        await self.events_manager.trigger_model_generation(reply, None)
        return reply

    async def _stream_completion(self, completion: typing.AsyncIterator):
        aggregator = MessageAggregator()
        try:  # stream response until canceled or finished
            async for packet in completion:
                reply = utils.parse_completion(packet, self.config.chat_model)
                # aggregate packet messages
                aggregator.add(reply)
                await self.events_manager.trigger_model_generation(
                    reply, aggregator
                )
        except (asyncio.CancelledError, KeyboardInterrupt):  # canceled
            aggregator.finish_reason = chatgpt.core.FinishReason.CANCELLED
        return aggregator.reply

    async def _cancelable(
        self, func: typing.Coroutine[typing.Any, typing.Any, T]
    ) -> T:
        # create the task and wait for it to finish
        self._model_task = asyncio.create_task(func)
        results = await self._model_task
        # cleanup
        self._model_task = None
        return results
