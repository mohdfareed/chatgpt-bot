# %%
import asyncio

import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.model
import chatgpt.tools
import chatgpt.types

console_handler = chatgpt.events.ConsoleHandler(
    chatgpt.types.SupportedModel.CHATGPT
)
memory = chatgpt.memory.ChatMemory(
    "00000", chatgpt.types.SupportedModel.CHATGPT
)
search_tool = chatgpt.tools.InternetSearch()
model_config = chatgpt.core.ModelConfig()
prompt = "You are a helpful assistant named ChatGPT."

model = chatgpt.model.ChatModel(
    model_config, memory, [search_tool], [console_handler]
)

# %%
memory.chat_history.clear()
message = chatgpt.core.UserMessage("Hi!")

# %%
memory.chat_history.add_message(message)
memory.messages

# %%
