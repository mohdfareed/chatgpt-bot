#!/usr/bin/env python3

# %%
import asyncio
import os
import sys

from dotenv import load_dotenv
from typing_extensions import override

# add package directory to the path
os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(os.getcwd())
# load environment variables
load_dotenv(override=True)
# add package directory to the path
os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(os.getcwd())
# load environment variables
load_dotenv(override=True)
# load the bot
import chatgpt.addons
import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.model
import chatgpt.tools

# TODO: rework as a console REPL app


class TestTool(chatgpt.tools.Tool):
    @override
    def name(self):
        return "hello134"  # name + 1

    @override
    def description(self):
        return "Says hello world to the user."  # text + 2

    @override
    def parameters(self):
        return [
            chatgpt.tools.ToolParameter(
                type="null",  # 2
                name="test_test_test",  # name + 1
                # description="1",  # text + 2
                # enum=["1"],  # 1
                optional=True,  # 1
            ),
        ]

    async def _run(self, query: str) -> str:
        return ""


console_handler = chatgpt.addons.ConsoleHandler()
prompt = "You are a helpful assistant named ChatGPT."
search_tools = [
    TestTool(),
    # TestTool(),
    # TestTool(),
    # TestTool(),
    # TestTool(),
]


# %%
async def main():
    try:
        memory = await chatgpt.memory.ChatMemory.initialize(
            "00000", in_memory=True
        )
        model = chatgpt.model.ChatModel(
            memory=memory,
            tools=search_tools,  # type: ignore
            handlers=[console_handler],
        )
        # await memory.initialize()
        await memory.history.clear()

        message = chatgpt.messages.UserMessage("Hi")
        await model.run(message)
        message = chatgpt.messages.UserMessage(
            "Do you know what my username is?"
        )
        await model.run(message)
        message = chatgpt.messages.UserMessage(
            "What's the metadata of your last message?"
        )
        await model.run(message)
    except Exception as e:
        raise e


asyncio.run(main())
