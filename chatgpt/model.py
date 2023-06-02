"""The OpenAI model used for generating completions."""

from typing import Optional

import openai
import tiktoken

from chatgpt.errors import *
from chatgpt.types import GPTChat


class ChatGPT():
    """ChatGPT model used for generating chat completions."""

    def __init__(self, model: Optional[str] = None, temperature=1.0,
                 presence_penalty=.0, frequency_penalty=.0):
        """Create a GPT model instance."""

        self.model = model or ChatGPT.available_models()[0]
        self.temperature = temperature
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty

    def params(self) -> dict[str, str | float]:
        """Get the model parameters to use in a chat completion request."""

        return dict(
            model=self.model,
            temperature=self.temperature,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
        )

    def tokens(self, string: str) -> int:
        """Get the number of tokens in a string using the model's tokenizer. If
        the model does not have a tokenizer, 'cl100k_base' is used.

        Args:
            text (str): The text to tokenize.

        Returns:
            int: The number of tokens in the text.
        """

        try:  # check if a model tokenizer is available
            encoding = tiktoken.encoding_for_model(self.model)
        except:  # the default tokenizer
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(string))

    def prompt_tokens(self, messages: GPTChat) -> int:
        """Get the number of tokens in a list of messages (a prompt).

        Args:
            messages (list[dict]): A list of messages forming a prompt. Each
            message is a dictionary of role, name, and content.

        Returns:
            int: The number of tokens in the prompt.
        """

        num_tokens = 1  # every prompt is primed with 1 token
        for message in messages.to_dict():
            num_tokens += 4  # every message has 4 tokens encoding
            for key, value in message.items():  # role, name, and content
                num_tokens += -1 if key == "name" else 0  # name omits role
                num_tokens += self.tokens(value)  # role and content
        num_tokens += 2  # every response is primed with 2 tokens
        return num_tokens

    @classmethod
    def available_models(cls) -> list[str]:
        """Get a list of available and supported models."""

        models_dict = dict(openai.Model.list())
        models = [model['id'] for model in models_dict['data']]
        return [model for model in models if 'gpt' in model]

    @property
    def model(self) -> str:
        """The model used for chat completions."""

        return self._model or ChatGPT.available_models()[0]

    @model.setter
    def model(self, model: Optional[str]) -> None:
        """Set the model used for chat completions. If no model is provided,
        the first available model will be used.

        Args:
            model (Optional[str]): The model name.

        Raises:
            InvalidParameterError: If the model provided is invalid.
        """

        if model not in self.available_models():
            raise InvalidParameterError("Invalid model name provided.")
        self._model = model

    @property
    def temperature(self) -> float:
        """The temperature of completions. Values are in range [0.0, 2.0].
        Higher values will result in more creative responses. Lower values will
        result in more deterministic responses."""

        return self._temperature

    @temperature.setter
    def temperature(self, temperature: float) -> None:
        """Set the temperature of completions.

        Args:
            temperature (float): The temperature of completions.

        Raises:
            InvalidParameterError: If value is not in the current range.
        """

        if (temperature < 0.0 or temperature > 2.0):
            error_msg = "Temperature must be in range [-2.0, 2.0]."
            raise InvalidParameterError(error_msg)
        self._temperature = temperature

    @property
    def presence_penalty(self) -> float:
        """The penalty for repeated tokens. Values are in range [-2.0, 2.0].
        Higher values will increase the likelihood of exploring new topics."""
        return self._presence_penalty

    @presence_penalty.setter
    def presence_penalty(self, presence_penalty: float) -> None:
        """Set the penalty for repeated tokens.

        Args:
            presence_penalty (float): The penalty for repeated tokens.

        Raises:
            InvalidParameterError: If value is not in the current range.
        """

        if (presence_penalty < -2.0 or presence_penalty > 2.0):
            error_msg = "Presence penalty must be in range [-2.0, 2.0]."
            raise InvalidParameterError(error_msg)
        self._presence_penalty = presence_penalty

    @property
    def frequency_penalty(self) -> float:
        """The penalty for tokens based on existence frequency. Values are in
        range [-2.0, 2.0]. Higher values decrease the likelihood to repeat
        lines verbatim."""

        return self._frequency_penalty

    @frequency_penalty.setter
    def frequency_penalty(self, frequency_penalty: float) -> None:
        """Set the penalty for tokens based on existing frequency.

        Args:
            frequency_penalty (float): The frequency based penalty for repeated
            tokens.

        Raises:
            InvalidParameterError: If value is not in the current range.
        """

        if (frequency_penalty < -2.0 or frequency_penalty > 2.0):
            error_msg = "Presence penalty must be in range [-2.0, 2.0]."
            raise InvalidParameterError(error_msg)
        self._frequency_penalty = frequency_penalty
