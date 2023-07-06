"""OpenAI metrics handler."""

import chatgpt
import chatgpt.events
import chatgpt.openai.tokenization


class MetricsHandler(chatgpt.events.ModelStart, chatgpt.events.ModelEnd):
    """Calculates request metrics as the model is used."""

    def __init__(self):
        super().__init__()
        self.prompts_tokens: int
        """The total number of tokens in all prompts."""
        self.generated_tokens: int
        """The total number of tokens in all generations."""
        self.tools_tokens: int
        """The total number of tokens taken by tools declarations."""
        self.cost: float
        """The total cost of all generations."""

    async def on_model_start(self, config, context, tools):
        self._model = config.model
        self._prompts = context
        self._tools = tools

        # reset metrics
        self.prompts_tokens = 0
        self.generated_tokens = 0
        self.tools_tokens = 0
        self.cost = 0.0
        self.has_tools = len(tools) > 0

    async def on_model_end(self, message):
        if not self._model:
            return

        # compute prompt tokens count
        self.prompts_tokens = chatgpt.openai.tokenization.messages_tokens(
            self._prompts, self._model
        )
        # compute generated tokens count
        self.generated_tokens = chatgpt.openai.tokenization.model_tokens(
            message, self._model, self.has_tools
        )
        # compute tools tokens count
        self.tools_tokens = chatgpt.openai.tokenization.tools_tokens(
            self._tools, self._model
        )

        self.cost = (  # compute cost of all tokens
            chatgpt.openai.tokenization.tokens_cost(
                self.prompts_tokens, self._model, is_reply=False
            )
            + chatgpt.openai.tokenization.tokens_cost(
                self.tools_tokens, self._model, is_reply=False
            )
            + chatgpt.openai.tokenization.tokens_cost(
                self.generated_tokens, self._model, is_reply=True
            )
        )

        # if reply includes usage, compare to computed usage
        if message.prompt_tokens or message.reply_tokens:
            if (
                message.prompt_tokens
                != self.prompts_tokens + self.tools_tokens
            ):
                chatgpt.logger.warning(
                    "Prompt tokens mismatch: {actual: %s, computed: %s}",
                    message.prompt_tokens,
                    self.prompts_tokens + self.tools_tokens,
                )
            if message.reply_tokens != self.generated_tokens:
                chatgpt.logger.warning(
                    "Reply tokens mismatch: {actual: %s, computed: %s}",
                    message.reply_tokens,
                    self.generated_tokens,
                )
