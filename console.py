# %%
import asyncio

import chatgpt.addons
import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.model
import chatgpt.supported_models
import chatgpt.tools


class TestTool(chatgpt.tools.Tool):
    def __init__(self):
        self.name = "hello134"  # name + 1
        self.description = "Now hello world how are you"  # text + 2

        self.parameters = [
            chatgpt.tools.ToolParameter(
                type="null",  # 2
                name="testisatest",  # name + 1
                # description="1",  # text + 2
                # enum=["1"],  # 1
                optional=True,  # 1
            ),
        ]

    async def _run(self, query: str) -> str:
        return ""


console_handler = chatgpt.addons.ConsoleHandler()
memory = chatgpt.memory.ChatMemory(
    "00000", -1, -1, chatgpt.supported_models.CHATGPT, True
)
search_tools = [
    TestTool(),
    # TestTool(),
    # TestTool(),
    # TestTool(),
    # TestTool(),
]
model_config = chatgpt.core.ModelConfig(
    model_name=chatgpt.supported_models.CHATGPT,
    # streaming=True,
)
prompt = "You are a helpful assistant named ChatGPT."

model = chatgpt.model.ChatModel(
    config=model_config,
    memory=memory,
    tools=search_tools,  # type: ignore
    handlers=[console_handler],
)


# %%
async def main():
    try:
        memory.history.clear()

        message = chatgpt.core.UserMessage("Hi")
        # memory.chat_history.add_message(message)
        # message = chatgpt.core.ToolUsage(
        #     "test_test_test_test", "{'test': True, 'test2': False, 'test3': 1}"
        # )
        # memory.chat_history.add_message(message)

        # message = chatgpt.core.UserMessage("How are you?")
        task = asyncio.create_task(model.run(message))
        await task
        # await asyncio.sleep(15)
        # await model.cancel()
    except:
        pass


asyncio.run(main())
