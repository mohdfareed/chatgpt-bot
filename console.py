# %%
import asyncio

import chatgpt.addons
import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.model
import chatgpt.tools


class TestTool(chatgpt.tools.Tool):
    def __init__(self):
        self.name = "test"
        self.description = ""  # text + 2

        self.parameters = [
            chatgpt.tools.ToolParameter(
                type="boolean",  # 2
                name="test",  # name + 1
                description="",  # text + 2
            ),
        ]

    async def _run(self, query: str) -> str:
        return ""


console_handler = chatgpt.addons.ConsoleHandler()
memory = chatgpt.memory.ChatMemory(
    "00000", -1, -1, chatgpt.core.SupportedModel.CHATGPT, True
)
search_tools = [TestTool()]
model_config = chatgpt.core.ModelConfig(
    model_name=chatgpt.core.SupportedModel.CHATGPT,
    # streaming=True,
)
prompt = "You are a helpful assistant named ChatGPT."

model = chatgpt.model.ChatModel(
    model=model_config,
    memory=memory,
    # tools=search_tools,  # type: ignore
    handlers=[console_handler],
)

# %%
memory.chat_history.clear()
message = chatgpt.core.UserMessage(
    "Hi, can you use the test function with random arguments you choose?"
)
# await model.generate(message)


# %%
async def main():
    try:
        task = asyncio.create_task(model.start(message))
        # await asyncio.sleep(15)
        # await model.cancel()
        await task
    except:
        pass


asyncio.run(main())
