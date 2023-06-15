"""The OpenAI model used for generating completions."""

import re
from typing import Any

from chatgpt import prompts, types
from database import Serializable


class ChatModel(Serializable):
    """ChatGPT model used for generating chat completions."""

    _temperature = None
    _presence_penalty = None
    _frequency_penalty = None

    model: str = types.ChatModel.CHATGPT
    """The model used for chat completions."""
    prompt: str = prompts.ASSISTANT_PROMPT
    """The system prompt of the model."""
    function_call: str | None = None
    """The name of the function the model must call. If None, the model will
    use any function. If the name is 'none', the model will not call any
    function."""
    max_tokens: int | None = None
    """The maximum number of tokens to generate. If None, the model will
    not be limited by the number of tokens."""

    @property
    def temperature(self) -> float:
        """The temperature of completions. Values are in range [0.0, 2.0].
        Higher values will result in more creative responses. Lower values will
        result in more deterministic responses."""
        return self._temperature or 1.0

    @temperature.setter
    def temperature(self, temperature: float) -> None:
        if temperature < 0.0 or temperature > 2.0:
            error_msg = "Temperature must be in range [-2.0, 2.0]."
            raise ValueError(error_msg)
        self._temperature = temperature

    @property
    def presence_penalty(self) -> float:
        """The penalty for repeated tokens. Values are in range [-2.0, 2.0].
        Higher values will increase the likelihood of exploring new topics."""
        return self._presence_penalty or 0.0

    @presence_penalty.setter
    def presence_penalty(self, presence_penalty: float) -> None:
        if presence_penalty < -2.0 or presence_penalty > 2.0:
            error_msg = "Presence penalty must be in range [-2.0, 2.0]."
            raise ValueError(error_msg)
        self._presence_penalty = presence_penalty

    @property
    def frequency_penalty(self) -> float:
        """The penalty for tokens based on existence frequency. Values are in
        range [-2.0, 2.0]. Higher values decrease the likelihood to repeat
        lines verbatim."""
        return self._frequency_penalty or 0.0

    @frequency_penalty.setter
    def frequency_penalty(self, frequency_penalty: float) -> None:
        if frequency_penalty < -2.0 or frequency_penalty > 2.0:
            error_msg = "Presence penalty must be in range [-2.0, 2.0]."
            raise ValueError(error_msg)
        self._frequency_penalty = frequency_penalty

    def params(self) -> dict[str, str | float | list[str] | None]:
        """Return the model parameters for a generation request."""
        # specify model function call behavior
        if self.function_call not in ("none", None):
            function_call = dict(name=self.function_call)
        else:
            function_call = self.function_call

        model_params = dict(
            model=self.model,
            function_call=function_call,
            max_tokens=self.max_tokens,
            temperature=self._temperature,
            presence_penalty=self._presence_penalty,
            frequency_penalty=self._frequency_penalty,
        )
        # remove None values
        return _clean_dict(model_params)


class ChatMessage(types.Message):
    """A message in a chat."""

    role: types.ChatMessageRole
    """The role of the message sender."""
    content: str
    """The content of the message."""

    @property
    def name(self) -> str | None:
        """The name of the message sender."""
        try:
            return self._name
        except AttributeError:
            return None

    @name.setter
    def name(self, name: str | None) -> None:
        pattern = r"^\w{1,64}$"
        if name and not re.match(pattern, name):
            raise ValueError("Name must be alphanumeric and 1-64 characters")
        self._name = name

    def to_message_dict(self) -> dict:
        message = dict(
            role=self.role,
            content=self.content,
            name=self.name,
        )
        return _clean_dict(message)


class ChatReply(types.ModelReply):
    """A reply to a message in a chat."""

    content: str | None = None
    """The content of the reply. It is None for function calls"""

    def to_message_dict(self) -> dict:
        message = dict(
            role=self.role,
            content=self.content,
        )
        return _clean_dict(message)


class FunctionCall(types.ModelReply):
    """A function call performed by a chat model."""

    name: str
    """The name of the function called."""
    arguments: dict[str, Any]
    """The arguments passed to the function."""

    def to_message_dict(self) -> dict:
        message = dict(
            role=self.role,
            function_call=dict(
                name=self.name,
                arguments=self.arguments,
            ),
        )
        return _clean_dict(message)


class FunctionResult(types.Message):
    """The result of a function call."""

    role: types.FunctionResultRole
    """The role of the message sender."""
    content: str
    """The content of the message."""

    @property
    def name(self) -> str:
        """The name of the message sender."""
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        pattern = r"^\w{1,64}$"
        if not re.match(pattern, name):
            raise ValueError("Name must be alphanumeric and 1-64 characters")
        self._name = name


def _clean_dict(dirty_dict: dict) -> dict:
    """Remove None values from a dictionary."""
    return {k: v for k, v in dirty_dict.items() if v is not None}
