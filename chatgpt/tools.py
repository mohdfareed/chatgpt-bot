"""Tools used by models to generate replies."""

import abc
import io
import sys
import typing

import wikipedia
from langchain import LLMMathChain, OpenAI
from langchain.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper

import chatgpt.core
from chatgpt import OPENAI_API_KEY, SERPER_API_KEY


class ToolsManager:
    """Manager of tools available to a model."""

    def __init__(self, tools: list["Tool"]):
        self.tools = tools
        """The tools available to the model."""

    async def use(self, tool_usage: chatgpt.core.ToolUsage):
        """Execute a tool."""
        tool = self._get_tool(tool_usage.tool_name)
        try:  # get the tool's result
            result = await tool.use(**tool_usage.arguments)
        except Exception as e:
            result = str(e)  # set result to error message
        return chatgpt.core.ToolResult(result, tool.name)

    def to_dict(self) -> list[dict]:
        """The tools available to the model as a dictionary."""
        return [tool.to_dict() for tool in self.tools]

    def _get_tool(self, tool_name: str):
        """Get a tool by name."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        raise ValueError("Invalid tool name")


class Tool(abc.ABC):
    """A tool that can be used by a model to generate replies."""

    name: str
    """The name of the tool."""
    description: str
    """A description of the tool."""
    parameters: list["ToolParameter"]
    """A list of parameters for the tool."""

    async def use(self, **kwargs: typing.Any):
        """Use the tool."""
        params = list(kwargs.keys())
        self._validate_params(params)
        return await self._run(**kwargs)

    @abc.abstractmethod
    async def _run(self, **kwargs: typing.Any) -> str:
        pass

    def to_dict(self):
        """Convert the tool to a json schema dictionary."""
        parameters = {param.name: param.to_dict() for param in self.parameters}
        req_params = [
            param.name for param in self.parameters if not param.optional
        ]
        req_params = req_params if len(req_params) > 0 else None

        tool_dict = dict(
            name=self.name,
            description=self.description,
            parameters=dict(
                type="object",
                properties=parameters,
                required=req_params,
            ),
        )
        return {k: v for k, v in tool_dict.items() if v is not None}

    def _validate_params(self, params: list[str]):
        possible_params = [param.name for param in self.parameters]
        required_params = [
            param.name for param in self.parameters if not param.optional
        ]

        for param in params:
            if param not in possible_params:
                raise TypeError(f"Invalid argument: {param}")
        for req_param in required_params:
            if req_param not in params:
                raise TypeError(f"Missing required argument: {req_param}")


class ToolParameter:
    """A parameter of a tool."""

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not str.isalnum(value.replace("_", "") or ""):
            raise TypeError("Name must be alphanumeric and 1-64 characters")
        self._name = value

    def __init__(
        self,
        type: str,
        name: str,
        description: str,
        enum: list[str] | None = None,
        optional: bool = False,
    ):
        self.type = type
        """The json type of the parameter."""
        self.name = name
        """The name of the parameter."""
        self.description = description
        """A description of the parameter."""
        self.enum = enum
        """A list of possible values for the parameter."""
        self.optional = optional
        """Whether the parameter is optional."""

    def to_dict(self):
        """Convert the parameter to a json schema dictionary."""
        params = dict(
            type=self.type,
            enum=self.enum,
            description=self.description,
        )
        return {k: v for k, v in params.items() if v is not None}


class InternetSearch(Tool):
    """A tool for searching the internet."""

    def __init__(self):
        self.name = "internet_search"
        self.description = (
            "Search the internet. Useful for finding up-to-date information "
            "about current events."
        )

        self.parameters = [
            ToolParameter(
                type="string",
                name="query",
                description="A targeted search query.",
            ),
        ]

    async def _run(self, query: str) -> str:
        return await GoogleSerperAPIWrapper(
            serper_api_key=SERPER_API_KEY
        ).arun(query)


class Calculator(Tool):
    """A tool for solving math problems."""

    def __init__(self):
        self.name = "calculator"
        self.description = (
            "Answer math questions. Useful for solving math problems."
        )

        self.parameters = [
            ToolParameter(
                type="string",
                name="expression",
                description="A valid numerical expression.",
            ),
        ]

    async def _run(self, expression: str) -> str:
        model = OpenAI(openai_api_key=OPENAI_API_KEY)  # type: ignore
        return await LLMMathChain.from_llm(model).arun(expression)


class WikiSearch(Tool):
    """A tool for searching Wikipedia."""

    def __init__(self):
        self.name = "wiki_search"
        self.description = (
            "Search Wikipedia. Useful for finding information about new or "
            "or unknown subjects and topics."
        )

        self.parameters = [
            ToolParameter(
                type="string",
                name="query",
                description="A targeted search query or subject.",
            ),
        ]

    async def _run(self, query: str) -> str:
        wiki_client = WikipediaAPIWrapper(wiki_client=wikipedia)
        return wiki_client.run(query)


class Python(Tool):
    """A tool for executing Python code."""

    def __init__(self):
        self.name = "python"
        self.description = (
            "Execute Python code. Useful for performing complex calculations"
            "and tasks. Equivalent to running in a Python shell. Only use it "
            "to run safe code. Can't include async code. Everything returned "
            "must be printed."
        )

        self.parameters = [
            ToolParameter(
                type="string",
                name="code",
                description="The Python code to execute.",
            ),
        ]

    def _run(self, code: str) -> str:
        local_vars = {}
        buffer = io.StringIO()
        stdout = sys.stdout
        sys.stdout = buffer

        try:
            exec(code, {}, local_vars)
        finally:
            sys.stdout = stdout

        output = buffer.getvalue()
        return (output or "").strip()
