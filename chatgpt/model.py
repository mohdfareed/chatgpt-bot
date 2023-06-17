"""Classes and functions used by different components of the ChatGPT package.
"""

import json
import typing

import openai

import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.tools
import chatgpt.types
import chatgpt.utils


class ChatModel:
    """Class responsible for interacting with the OpenAI API."""

    def __init__(
        self,
        model: chatgpt.core.ModelConfig,
        memory: chatgpt.memory.ChatMemory,
        tools: list[chatgpt.tools.Tool] = [],
        handlers: list[chatgpt.events.CallbackHandler] = [],
    ) -> None:
        self._metrics = chatgpt.events.MetricsHandler(model.model_name)
        handlers = handlers + [self._metrics]

        self.model = model
        """The model's configuration."""
        self.memory = memory
        """The memory of the model."""
        self.tools_manager = chatgpt.tools.ToolsManager(tools)
        """The manager of tools available to the model."""
        self.events_manager = chatgpt.events.EventsManager(handlers)
        """The events manager of callback handlers."""

    async def generate(self, message: chatgpt.core.UserMessage):
        """Generate a response to a list of messages. None on error."""

        # add message to memory
        self.memory.chat_history.add_message(message)
        # trigger model start event
        await self.events_manager.trigger_model_start(
            self.memory.chat_history.messages
        )

        try:  # generate reply
            deep_handlers = self.events_manager.deep_handlers
            deep_manager = chatgpt.events.EventsManager(deep_handlers)
            reply = await self._call(deep_manager)
        except Exception as e:
            await self.events_manager.trigger_model_error(e)
            return

        # return reply
        await self.events_manager.trigger_model_exit(reply)
        return reply

    async def _call(self, manager: chatgpt.events.EventsManager):
        reply = None

        while type(reply) is not chatgpt.core.ModelMessage:
            # generate response
            response: dict = await completion(**self._params())  # type: ignore
            await self.events_manager.trigger_model_generation_end(response)
            # parse and store response as reply
            reply = parse_completion(response, self.model.model_name)
            self.memory.chat_history.add_message(reply)

            # use tool if necessary
            if type(reply) == chatgpt.core.ToolUsage:
                # get tool results
                await manager.trigger_tool_use(reply)
                results = await self.tools_manager.use(reply)
                # store tool results
                self.memory.chat_history.add_message(results)
                await manager.trigger_tool_result(results)

        return reply

    def _params(self):
        messages = [m.to_message_dict() for m in self.memory.messages]
        if self.model.prompt:
            messages.insert(0, self.model.prompt.to_message_dict())
        return dict(
            messages=messages,
            functions=self.tools_manager.to_dict(),
            **self.model.params(),
        )


@chatgpt.utils.retry_decorator()
async def completion(**kwargs) -> typing.AsyncIterator[dict] | dict:
    """Use tenacity to retry the async completion call."""
    return await openai.ChatCompletion.acreate(**kwargs)  # type: ignore


def parse_completion(
    completion: dict,
    model: chatgpt.types.SupportedModel,
) -> chatgpt.core.ModelMessage | chatgpt.core.ToolUsage:
    """Parse a completion response from the OpenAI API."""

    # parse metadata
    finish_reason = chatgpt.types.FinishReason(
        completion["choices"][0]["finish_reason"]
    )
    prompt_tokens = completion["usage"]["prompt_tokens"]
    prompt_cost = chatgpt.utils.tokens_cost(
        prompt_tokens, model, is_reply=False
    )
    reply_tokens = completion["usage"]["completion_tokens"]
    completion_cost = chatgpt.utils.tokens_cost(
        reply_tokens, model, is_reply=True
    )

    # parse reply
    message = completion["choices"][0]["message"]
    if content := message.get("content"):
        reply = chatgpt.core.ModelMessage(content)
    elif function_call := message.get("function_call"):
        reply = chatgpt.core.ToolUsage(**json.loads(function_call))
    else:
        raise ValueError("Invalid completion message received")

    # load metadata
    reply.cost = prompt_cost + completion_cost
    reply.prompt_tokens = prompt_tokens
    reply.reply_tokens = reply_tokens
    reply.finish_reason = finish_reason
    return reply
