"""The supported OpenAI GPT models."""


class SupportedModel:
    """A supported GPT model."""

    def __init__(
        self, name: str, size: int, input_cost: float, output_cost: float
    ):
        self._name = name
        self._size = size
        self._input_cost = input_cost
        self._output_cost = output_cost

    @property
    def name(cls) -> str:
        """The name of the model."""
        return cls._name

    @property
    def size(cls) -> int:
        """The size of input the model can accept in tokens."""
        return cls._size

    @property
    def input_cost(cls) -> float:
        """The cost of input tokens, in USD and per 1k tokens."""
        return cls._input_cost

    @property
    def output_cost(cls) -> float:
        """The cost of output tokens, in USD and per 1k tokens."""
        return cls._output_cost


CHATGPT = SupportedModel("gpt-3.5-turbo-0613", 4000, 0.0015, 0.002)
"""The supported GPT-3.5 model."""
CHATGPT_16K = SupportedModel("gpt-3.5-turbo-16k", 16000, 0.003, 0.004)
"""The supported GPT-3.5 model with extended size."""
GPT4 = SupportedModel("gpt-4", 8000, 0.03, 0.06)
"""The supported GPT-4 model."""
GPT4_16K = SupportedModel("gpt-4-16k", 32000, 0.06, 0.12)
"""A supported GPT-4 model with extended size."""
