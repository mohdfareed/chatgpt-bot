"""The supported OpenAI models."""

import chatgpt.core

CHATGPT = chatgpt.core.SupportedChatModel(
    "gpt-3.5-turbo-0613",
    size=4000,
    input_cost=0.0015,
    output_cost=0.002,
)
"""The supported GPT-3.5 model."""

CHATGPT_16K = chatgpt.core.SupportedChatModel(
    "gpt-3.5-turbo-16k",
    size=16000,
    input_cost=0.003,
    output_cost=0.004,
)
"""The supported GPT-3.5 model with extended size."""

GPT4 = chatgpt.core.SupportedChatModel(
    "gpt-4",
    size=8000,
    input_cost=0.03,
    output_cost=0.06,
)
"""The supported GPT-4 model."""

GPT4_16K = chatgpt.core.SupportedChatModel(
    "gpt-4-16k",
    size=32000,
    input_cost=0.06,
    output_cost=0.12,
)
"""A supported GPT-4 model with extended size."""
