"""OpenAI API models interface."""

import asyncio
import json
import logging
import typing

import openai.error
import tenacity

import chatgpt.core
import chatgpt.events
import chatgpt.openai.supported_models
import chatgpt.openai.tokenization
import chatgpt.tools
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
        self._generator: asyncio.Task | None = None
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
        if self._generator is not None:
            self._generator.cancel()
            interrupted = True
        if self._running:
            self._running = False
            interrupted = True

        if interrupted:  # trigger interrupt event
            await self.events_manager.trigger_model_interrupt()

    async def run(self, messages: list[chatgpt.core.Message]):
        """Run the model."""
        # example implementation of the model's run method

        # broadcast input and start running the model
        await self.events_manager.trigger_model_run(messages)
        reply = await self._run_model(self._core_logic(messages))
        # broadcast reply if any
        if isinstance(reply, chatgpt.core.ModelMessage):
            await self.events_manager.trigger_model_reply(reply)
        return reply

    async def _core_logic(self, messages: list[chatgpt.core.Message]):
        # example implementation of the model's core logic
        return await self._generate_reply(messages)

    async def _run_model(
        self, core_logic: typing.Coroutine[typing.Any, typing.Any, T]
    ) -> T:
        if self._running or self._generator is not None:
            raise chatgpt.core.ModelError("Model is already running")

        try:  # generate reply
            self._running = True
            reply = await core_logic
        except Exception as e:  # handle errors
            await self.events_manager.trigger_model_error(e)
            raise chatgpt.core.ModelError("Failed to generate a reply") from e
        finally:  # cleanup
            self._generator = None
            self._running = False
        return reply

    async def _generate_reply(self, messages: list[chatgpt.core.Message]):
        # generate a reply to a list of messages
        params = (self.config, messages, self.tools_manager.tools)
        await self.events_manager.trigger_model_start(*params)
        reply = await self._request_completion(*params)
        # FIXME: filter metadata out of reply's text if accidentally included

        # trigger model end event if model was not canceled
        if not isinstance(reply, chatgpt.core.ModelMessage):
            return None  # canceled
        await self.events_manager.trigger_model_end(reply)

        # fix reply metrics
        reply.reply_tokens = self._metrics.generated_tokens
        reply.prompt_tokens = self._metrics.prompts_tokens
        reply.prompt_tokens += self._metrics.tools_tokens
        reply.cost = self._metrics.cost
        return reply

    async def _request_completion(self, *params):
        # request response from openai
        request = _create_completion_params(*params)
        completion = await self._cancelable(_generate_completion(**request))
        if completion is None:  # canceled
            return completion

        # return streamed response if streaming
        if self.config.streaming:  # triggers model generation events
            return await self._cancelable(self._stream_completion(completion))  # type: ignore

        # return processed response if not streaming
        reply = _parse_completion(completion, self.config.model)  # type: ignore
        await self.events_manager.trigger_model_generation(reply, None)
        return reply

    async def _stream_completion(self, completion: typing.AsyncIterator):
        aggregator = MessageAggregator()
        try:  # start a task to parse the completion packets
            async for packet in completion:
                reply = _parse_completion(packet, self.config.model)
                # aggregate messages into one
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
        self._generator = asyncio.create_task(func)
        results = await self._generator
        self._generator = None
        return results


def retry(min_wait=1, max_wait=60, max_attempts=6):
    log = tenacity.before_sleep_log(chatgpt.logger, logging.WARNING)
    retry_exceptions = (
        openai.error.Timeout,
        openai.error.APIError,
        openai.error.APIConnectionError,
        openai.error.RateLimitError,
        openai.error.ServiceUnavailableError,
    )

    return tenacity.retry(
        reraise=True,
        stop=tenacity.stop_after_attempt(max_attempts),
        wait=tenacity.wait_random_exponential(min=min_wait, max=max_wait),
        retry=tenacity.retry_if_exception_type(retry_exceptions),
        before_sleep=log,
    )


@retry()
async def _generate_completion(
    **kwargs: typing.Any,
) -> typing.AsyncIterator[dict] | dict | None:
    try:
        return await openai.ChatCompletion.acreate(**kwargs)  # type: ignore
    except (asyncio.CancelledError, KeyboardInterrupt):
        return None


def _create_completion_params(
    config: chatgpt.core.ModelConfig,
    messages: list[chatgpt.core.Message],
    tools: list[chatgpt.tools.Tool],
) -> dict:
    messages_dict = [m.to_message_dict() for m in messages]
    tools_dict = [t.to_dict() for t in tools]

    # can't send empty list of tools
    if len(tools_dict) < 1:
        tools_dict = None

    # create parameters dict
    parameters = dict(
        messages=messages_dict,
        functions=tools_dict,
        **config.to_dict(),
    )
    # remove None values
    return _clean_params(parameters)  # type: ignore


def _parse_completion(
    completion: dict,
    model: chatgpt.core.SupportedChatModel,
) -> chatgpt.core.ModelMessage:
    choice: dict = completion["choices"][0]
    message: dict = choice.get("message") or choice.get("delta") or {}

    # parse message
    content = message.get("content") or ""
    if function_call := message.get("function_call"):
        reply_dict: dict = json.loads(str(function_call))
        name = reply_dict.get("name") or ""  # default to empty name
        args = reply_dict.get("arguments") or "{}"  # default to empty dict

        reply = chatgpt.core.ToolUsage(name, args)
        reply.content = content
    else:  # default to a model message
        reply = chatgpt.core.ModelMessage(content)

    # load metadata
    reply = _parse_usage(completion, reply, model)
    reply = _parse_finish_reason(completion, reply)
    return reply


def _parse_finish_reason(completion, reply: chatgpt.core.ModelMessage):
    finish_reason = completion["choices"][0]["finish_reason"]
    if not finish_reason:
        reply.finish_reason = chatgpt.core.FinishReason.UNDEFINED
        return reply
    reply.finish_reason = chatgpt.core.FinishReason(finish_reason)
    return reply


def _parse_usage(
    completion,
    reply: chatgpt.core.ModelMessage,
    model: chatgpt.core.SupportedChatModel,
):
    try:  # default to 0 if not present
        prompt_tokens = completion["usage"]["prompt_tokens"]
        reply_tokens = completion["usage"]["completion_tokens"]
    except KeyError:
        prompt_tokens = 0
        reply_tokens = 0

    prompt_cost = chatgpt.openai.tokenization.tokens_cost(
        prompt_tokens, model, is_reply=False
    )
    completion_cost = chatgpt.openai.tokenization.tokens_cost(
        reply_tokens, model, is_reply=True
    )
    reply.prompt_tokens = prompt_tokens
    reply.reply_tokens = reply_tokens
    reply.cost = prompt_cost + completion_cost
    return reply


def _clean_params(params):
    if isinstance(params, dict):
        for key, value in list(params.items()):
            if isinstance(value, (list, dict, tuple, set)):
                params[key] = _clean_params(value)
            elif value is None or key is None:
                del params[key]
    elif isinstance(params, (list, set, tuple)):
        params = type(params)(
            _clean_params(item) for item in params if item is not None
        )
    return params
