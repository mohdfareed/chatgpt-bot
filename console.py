# %%
import asyncio

import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.model
import chatgpt.tools
import chatgpt.types

console_handler = chatgpt.events.ConsoleHandler()
memory = chatgpt.memory.ChatMemory(
    "00000", chatgpt.types.SupportedModel.CHATGPT
)
search_tools = [chatgpt.tools.Python(), chatgpt.tools.InternetSearch()]
model_config = chatgpt.core.ModelConfig(
    model_name=chatgpt.types.SupportedModel.CHATGPT_16K
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
asyncio.run(model.generate(message))

prompt_metrics = model._metrics.prompts_tokens
reply_metrics = model._metrics.generated_tokens

# %%
# memory.chat_history.add_message(message)
# memory.messages

# %%
