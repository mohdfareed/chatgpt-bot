# %%
import asyncio

import chatgpt.addons
import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.model
import chatgpt.tools

console_handler = chatgpt.addons.ConsoleHandler(streaming=True)
memory = chatgpt.memory.ChatMemory(
    "00000", chatgpt.core.SupportedModel.CHATGPT
)
search_tools = [chatgpt.addons.Calculator, chatgpt.addons.InternetSearch()]
model_config = chatgpt.core.ModelConfig(
    model_name=chatgpt.core.SupportedModel.CHATGPT_16K
)
prompt = "You are a helpful assistant named ChatGPT."

model = chatgpt.model.ChatModel(
    model_config, memory, search_tools, [console_handler]
)

# %%
memory.chat_history.clear()
message = chatgpt.core.UserMessage(
    "Search for 'python' and tell me the results."
)
# await model.generate(message)


# %%
async def main():
    task = asyncio.create_task(model.start(message, stream=True))
    await asyncio.sleep(1.5)

    await model.cancel()
    await task


asyncio.run(main())
