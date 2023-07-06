# %%
import asyncio

import chatgpt.addons
import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.model
import chatgpt.openai.supported_models
import chatgpt.tools

# TODO: rework as a console interface


class TestTool(chatgpt.tools.Tool):
    def __init__(self):
        self.name = "hello134"  # name + 1
        self.description = "Says hello world to the user."  # text + 2

        self.parameters = [
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
        print("Initializing memory...")
        memory = await chatgpt.memory.ChatMemory.initialize(
            "00000", -1, -1, False
        )
        model_config = chatgpt.core.ModelConfig(
            model=chatgpt.openai.supported_models.CHATGPT,
            prompt=prompt,
            streaming=True,
        )
        model = chatgpt.model.ChatModel(
            memory=memory,
            tools=search_tools,  # type: ignore
            handlers=[console_handler],
        )
        # await memory.initialize()
        print("Initializing model...")
        await memory.history.clear()
        await memory.history.set_model(model_config)

        message = chatgpt.core.UserMessage("Hi")
        # memory.chat_history.add_message(message)
        # message = chatgpt.core.ToolUsage(
        #     "test_test_test_test", "{'test': True, 'test2': False, 'test3': 1}"
        # )
        # memory.chat_history.add_message(message)

        # message = chatgpt.core.UserMessage("How are you?")
        task = asyncio.create_task(model.run(message))
        print("Running model...")
        await task
        # await asyncio.sleep(15)
        # await model.cancel()
    except Exception as e:
        raise e


asyncio.run(main())
