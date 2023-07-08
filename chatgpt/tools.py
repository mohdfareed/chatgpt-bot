"""Tools used by models to generate replies."""

import abc
import asyncio
import importlib
import inspect
import pkgutil
import typing

import chatgpt.core


class ToolsManager:
    """Manager of tools available to a model."""

    def __init__(self, tools: list["Tool"]):
        self.tools = tools
        """The tools available to the model."""

    async def use(self, tool_usage: chatgpt.core.ToolUsage):
        """Execute a tool."""
        result = None
        tool = Tool.from_tool_name(tool_usage.tool_name)
        try:  # get the tool's result
            result = await tool.use(**tool_usage.arguments)
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass  # canceled
        except Exception as e:
            result = str(e)  # return error message

        if result is not None:
            result = chatgpt.core.ToolResult(result, tool.name)
        return result


class Tool(chatgpt.core.Serializable, abc.ABC):
    """A tool that can be used by a model to generate replies."""

    @abc.abstractproperty
    def name(self) -> str:  # type: ignore
        """The name of the tool."""
        pass

    @abc.abstractproperty
    def description(self) -> str:  # type: ignore
        """A description of the tool."""
        pass

    @abc.abstractproperty
    def parameters(self) -> list["ToolParameter"]:  # type: ignore
        """A list of parameters for the tool."""
        pass

    @abc.abstractmethod
    async def _run(self, **kwargs: typing.Any) -> str:
        """The method's arguments must match the tool's parameters."""
        pass

    async def use(self, **kwargs: typing.Any):
        """Use the tool."""
        params = list(kwargs.keys())
        self._validate_params(params)
        return await self._run(**kwargs)

    @classmethod
    def available_tools(cls):
        """Returns all the available tools."""
        if not inspect.isabstract(cls):
            yield cls()  # type: ignore
        # for sub_tool in cls.__subclasses__():
        #     yield from sub_tool.available_tools()
        for _, name, _ in pkgutil.walk_packages():
            module = importlib.import_module(name)
            for _, sub_tool in inspect.getmembers(module, inspect.isclass):
                if issubclass(sub_tool, cls):
                    yield sub_tool()

    @classmethod
    def from_tool_name(cls, tool_name: str):
        """Get a tool by name."""
        for tool in cls.available_tools():
            if tool.name == tool_name:
                return tool
        raise ValueError("Invalid tool name")

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
