"""Parsers of agents output."""

import re
from typing import Union

from langchain.agents.conversational_chat import output_parser
from langchain.schema import AgentAction, AgentFinish, OutputParserException

from chatgpt import prompts


class ChatGPTOutputParser(output_parser.ConvoOutputParser):
    def get_format_instructions(self) -> str:
        return prompts.INSTRUCTIONS

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:  # parse action and its input
            action_str = re.search(r"Action: (.*?)\n", text).group(1).strip()
            input_str = text.split("Input: ")[-1].strip()
        except:
            raise OutputParserException(f"Invalid LLM output: `{text}`")
        if action_str == "Final Message":
            return AgentFinish({"output": input_str}, text)
        return AgentAction(action_str, input_str, text)

    @property
    def _type(self) -> str:
        return "conversational"
