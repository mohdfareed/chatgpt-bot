"""OpenAI chat model implementation."""

import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.tools
import chatgpt.utils


class ChatModel:
    """Class responsible for interacting with the OpenAI API."""

    def __init__(
        self,
        model: chatgpt.core.ModelConfig,
        memory: chatgpt.memory.ChatMemory,
        tools: list[chatgpt.tools.Tool] = [],
        handlers: list[chatgpt.events.ModelEvent] = [],
    ) -> None:
        self._metrics = chatgpt.events.MetricsHandler()
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
        await self.events_manager.trigger_model_start(
            self.model,
            self.memory.messages,
            self.tools_manager.tools,
        )

        try:  # generate reply
            reply = await self._call()
        except Exception as e:
            await self.events_manager.trigger_model_error(e)
            raise ModelError("Failed to generate reply") from e
        await self.events_manager.trigger_model_reply(reply)
        return reply

    async def _call(self):
        reply = None

        while type(reply) is not chatgpt.core.ModelMessage:
            # generate response
            response = await self._request()
            reply = chatgpt.utils.parse_completion(
                response, self.model.model_name
            )
            await self.events_manager.trigger_model_end(reply)

            # fix and store response as reply
            reply.prompt_tokens = self._metrics.prompts_tokens
            reply.reply_tokens = self._metrics.generated_tokens
            self.memory.chat_history.add_message(reply)

            # use tool if necessary
            if type(reply) == chatgpt.core.ToolUsage:
                await self.events_manager.trigger_tool_use(reply)
                # get tool results
                results = await self.tools_manager.use(reply)
                await self.events_manager.trigger_tool_result(results)
                # store tool results
                self.memory.chat_history.add_message(results)

        return reply

    async def _request(self):
        response: dict = await chatgpt.utils.completion(**self._params())  # type: ignore

        message = response["choices"][0]["message"]
        if content := message.get("content"):
            message = content
        elif function_call := message.get("function_call"):
            message = str(function_call)
        await self.events_manager.trigger_model_generation(message)

        return response

    def _params(self):
        messages = [m.to_message_dict() for m in self.memory.messages]
        if self.model.prompt:
            messages.insert(0, self.model.prompt.to_message_dict())

        parameters = dict(
            messages=messages,
            functions=self.tools_manager.to_dict(),
            **self.model.params(),
        )
        return parameters


class ModelError(Exception):
    """Exception raised for model errors."""
