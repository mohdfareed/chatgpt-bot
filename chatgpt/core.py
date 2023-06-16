"""Classes and functions used by different components of the ChatGPT package.
"""


from chatgpt import events, memory, models, tools, types, utils


class ChatModel:
    """Class responsible for interacting with the OpenAI API."""

    def __init__(
        self,
        model: models.ModelConfig,
        memory: memory.ChatMemory,
        tools: list[tools.Tool],
        handlers: list[events.CallbackHandler],
    ) -> None:
        self.model = model
        """The model's configuration."""
        self.memory = memory
        """The memory of the model."""
        self.tools = tools
        """The tools available to the model."""
        self.events_manager = events.EventsManager(handlers)
        """The events manager of callback handlers."""


class MetricsHandler(events.CallbackHandler):
    """Calculates request metrics."""

    def __init__(self, model: types.SupportedModel):
        super().__init__()
        self._prompts: list[dict[str, str]] = []
        self.reply_only = False
        self.model = model
        """The model used for reply generation."""
        self.prompts_tokens = 0
        """The total number of tokens in all prompts."""
        self.generated_tokens = 0
        """The total number of tokens in all generations."""

    async def on_generation_start(self, messages):
        # track all prompts
        self._prompts += messages

    async def on_generation_end(self, generation):
        # calculate tokens for all generations
        self.generated_tokens += utils.tokens(generation, self.model)
        self.prompts_tokens += utils.messages_tokens(self._prompts, self.model)
