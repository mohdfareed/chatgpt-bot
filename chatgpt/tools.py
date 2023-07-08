"""Tools used by models to generate replies."""

import abc
import asyncio
import typing

import chatgpt.core


class ToolsManager:
    """Manager of tools available to a model."""

    def __init__(self, tools: list["Tool"]):
        self.tools = tools
        """The tools available to the model."""

    async def use(self, tool_usage: chatgpt.core.ToolUsage):
        """Execute a tool."""
        tool = self._get_tool(tool_usage.tool_name)
        result = None
        try:  # get the tool's result
            result = await tool.use(**tool_usage.arguments)
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass  # canceled
        except Exception as e:
            result = str(e)  # return error message

        if result is not None:
            result = chatgpt.core.ToolResult(result, tool.name)
        return result

    def _get_tool(self, tool_name: str):
        """Get a tool by name."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        raise ValueError("Invalid tool name")


class Tool(chatgpt.core.Serializable, abc.ABC):
    """A tool that can be used by a model to generate replies."""

    def __init__(
        self,
        name: str,
        description: str | None = None,
        parameters: list["ToolParameter"] = [],
        **kwargs: typing.Any,
    ):
        self.name = name
        """The name of the tool."""
        self.description = description
        """A description of the tool."""
        self.parameters = parameters
        """A list of parameters for the tool."""
        super().__init__(**kwargs)

    async def use(self, **kwargs: typing.Any):
        """Use the tool."""
        params = list(kwargs.keys())
        self._validate_params(params)
        return await self._run(**kwargs)

    @abc.abstractmethod
    async def _run(self, **kwargs: typing.Any) -> str:
        """The method's arguments must match the tool's parameters' types and
        names."""
        pass

    def to_dict(self):
        """Convert the tool to an OpenAPI dictionary."""
        parameters = {param.name: param.to_dict() for param in self.parameters}
        req_params = [
            param.name for param in self.parameters if not param.optional
        ]
        req_params = req_params if len(req_params) > 0 else None

        return dict(
            name=self.name,
            description=self.description,
            parameters=dict(
                type="object",
                properties=parameters,
                required=req_params,
            ),
        )

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


class ToolParameter(chatgpt.core.Serializable):
    """A parameter of a tool."""

    def __init__(
        self,
        type: str,
        name: str,
        description: str | None = None,
        enum: list[str] | None = None,
        optional: bool = False,
        **kwargs: typing.Any,
    ):
        self.type = type
        """The json type of the parameter."""
        self.name = name
        """The name of the parameter. Must be alphanumeric and 1-64 chars."""
        self.description = description
        """A description of the parameter."""
        self.enum = enum
        """A list of possible values for the parameter."""
        self.optional = optional
        """Whether the parameter is optional."""
        super().__init__(**kwargs)

    def to_dict(self):
        """Convert the parameter to an OpenAPI dictionary."""
        return dict(
            type=self.type,
            enum=self.enum,
            description=self.description,
        )
