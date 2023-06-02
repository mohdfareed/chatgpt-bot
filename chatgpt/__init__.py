"""ChatGPT package containing multiple completions implementations."""

import logging
import os

import openai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
"""The environment's OpenAI API key for message generation."""
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
"""The environment's Serper API key for Google search."""
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
"""The environment's Serper API key for Google search."""

logger = logging.getLogger(__name__)
"""The logger for the ChatGPT module."""

try:  # validate OpenAI API key
    openai.api_key = OPENAI_API_KEY
    _ = openai.Model.list()
except:
    raise
