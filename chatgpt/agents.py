"""The available agents and their parsers."""

from langchain import OpenAI
from langchain.agents import AgentType, Tool, initialize_agent
from langchain.chains import ConversationChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate

from chatgpt import OPENAI_API_KEY, core
from chatgpt import memory as mem
from chatgpt import parsers, prompts


class ChatGPT:
    """GPT-based chat agent."""

    def __init__(
        self,
        memory=mem.ChatMemory(2500),
        system_prompt=prompts.ASSISTANT_PROMPT,
        temperature=1.0,
        token_handler=None,
        openai_api_key=OPENAI_API_KEY,
    ):
        """Initialize the agent.

        Args:
            temperature (float, optional): Model's temperature.
            memory (BaseChatMemory, optional): Agent memory.
            system_message (_type_, optional): Prompt of the model's persona.
        """

        prompt = system_prompt + prompts.CHAT_INSTRUCTIONS
        handler = None
        if token_handler:
            handler = dict(callbacks=[core.StreamHandler(token_handler)])
        model = ChatOpenAI(
            temperature=0.1,
            openai_api_key=openai_api_key,
            streaming=True,
            **(handler or dict()),
        )  # type: ignore
        self.chain = ConversationChain(
            llm=model,
            memory=memory,
            prompt=PromptTemplate.from_template(prompt),
        )

    async def generate(
        self,
        message: str,
        metadata: dict[str, str],
        reply_metadata: dict[str, str],
    ) -> core.GenerationResults:
        """Generate a response to an input message.

        returns:
            int: The token usage of the request.
        """

        input = self._parse_inputs(message, metadata, reply_metadata)
        with core.MetricsHandler.callback() as metrics_callback:
            self.generation = self.chain.arun(input)
            generated_text = await self.generation
            results = core.GenerationResults(generated_text, metrics_callback)
        return results

    async def stop(self) -> None:
        """Cancel the model's current generation task."""
        self.generation.close()

    def _parse_inputs(self, message, metadata, reply_metadata) -> str:
        """Parse a message for the agent."""
        message_prompt = parse_message(message, metadata, "user")
        message_prompt += parse_message("", reply_metadata, "you")
        return message_prompt


class ChatGPTTools:
    """GPT-based chat agent."""

    def __init__(
        self,
        tools: list[Tool],
        memory=mem.ChatMemory(2500),
        system_prompt=prompts.ASSISTANT_PROMPT,
        temperature=1.0,
        openai_api_key=OPENAI_API_KEY,
    ):
        """Initialize the agent.

        Args:
            temperature (float, optional): Model's temperature.
            memory (BaseChatMemory, optional): Agent memory.
            system_message (_type_, optional): Prompt of the model's persona.
        """

        agent_params = dict(
            prefix=system_prompt,
            format_instructions=prompts.INSTRUCTIONS,
            suffix=prompts.SUFFIX,
            ai_prefix="",
            output_parser=parsers.ChatGPTOutputParser(),
        )
        agent_model = OpenAI(
            temperature=temperature, openai_api_key=openai_api_key
        )  # type: ignore
        self.agent = initialize_agent(
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            llm=agent_model,
            tools=tools,
            memory=memory,
            agent_kwargs=agent_params,
            handle_parsing_errors=True,
            verbose=True,
        )

    async def generate(
        self,
        message: str,
        metadata: dict[str, str],
        reply_metadata: dict[str, str],
    ) -> str:
        """Generate a response to an input message."""

        input = self._parse_message_prompt(message, metadata, reply_metadata)
        return await self.agent.arun(input)

    async def stop(self) -> None:
        """Cancel the agent's current task."""
        self.agent.max_execution_time = 0

    def _parse_message_prompt(self, message, metadata, reply_metadata) -> str:
        """Parse a message for the agent."""

        # construct metadata
        metadata_str = self._format_metadata(metadata)
        reply_metadata_str = self._format_metadata(reply_metadata)
        # construct message
        message_prompt = f"\n[user | {metadata_str}] {message}"
        message_prompt += f"\n[you | {reply_metadata_str}] "
        return message_prompt

    def _format_metadata(self, metadata: dict[str, str]) -> str:
        """Format metadata for an agent message."""

        metadata_str = ""
        for key, value in metadata.items():
            metadata_str += f"{key}: {value} | "
        # remove trailing '|'
        metadata_str = metadata_str.rstrip(" | ")
        return metadata_str


def parse_message(message: str, metadata: dict[str, str], sender: str) -> str:
    """Parse a message and its metadata into a prompt."""

    # construct metadata
    metadata_str = _format_metadata(metadata)
    # construct message
    message_prompt = f"\n[{sender} | {metadata_str}] {message}"
    return message_prompt


def _format_metadata(metadata: dict[str, str]) -> str:
    """Format metadata for an agent message."""

    metadata_str = ""
    for key, value in metadata.items():
        metadata_str += f"{key}: {value} | "
    # remove trailing '|'
    metadata_str = metadata_str.rstrip(" | ")
    return metadata_str
