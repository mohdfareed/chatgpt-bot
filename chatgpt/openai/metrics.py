"""OpenAI metrics handler."""

from typing_extensions import override

import chatgpt
import chatgpt.events
import chatgpt.openai.tokenization


class MetricsHandler(chatgpt.events.ModelStart, chatgpt.events.ModelEnd):
    """Calculates request metrics as the model is used."""

    @override
    async def on_model_start(self, config, context, tools):
        self._model = config.chat_model
        self._prompts = context
        self._tools = tools

    @override
    async def on_model_end(self, message):
        if not self._model:
            return

        # compute prompt tokens count
        prompts_tokens = chatgpt.openai.tokenization.messages_tokens(
            self._prompts, self._model
        )
        # compute generated tokens count
        generated_tokens = chatgpt.openai.tokenization.model_tokens(
            message, self._model, len(self._tools) > 0
        )
        # compute tools tokens count
        tools_tokens = chatgpt.openai.tokenization.tools_tokens(
            self._tools, self._model
        )

        cost = (  # compute cost of all tokens
            chatgpt.openai.tokenization.tokens_cost(
                prompts_tokens, self._model, is_reply=False
            )
            + chatgpt.openai.tokenization.tokens_cost(
                tools_tokens, self._model, is_reply=False
            )
            + chatgpt.openai.tokenization.tokens_cost(
                generated_tokens, self._model, is_reply=True
            )
        )

        # if reply includes usage, compare to computed usage
        if message.prompt_tokens or message.reply_tokens:
            if message.prompt_tokens != prompts_tokens + tools_tokens:
                chatgpt.logger.warning(
                    "Prompt tokens mismatch: {actual: %s, computed: %s}",
                    message.prompt_tokens,
                    prompts_tokens + tools_tokens,
                )
                chatgpt.logger.warning(f"Message: {message.serialize()}")
            if message.reply_tokens != generated_tokens:
                chatgpt.logger.warning(
                    "Reply tokens mismatch: {actual: %s, computed: %s}",
                    message.reply_tokens,
                    generated_tokens,
                )
                chatgpt.logger.warning(f"Message: {message.serialize()}")

        # update the message's usage
        message.prompt_tokens = prompts_tokens + tools_tokens
        message.reply_tokens = generated_tokens
        message.cost = cost
