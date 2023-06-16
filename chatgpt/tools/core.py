"""Tools used by models to generate replies."""

import abc


class ToolParameter:
    """A parameter of a tool."""

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
        return dict(
            type=self.type,
            enum=self.enum,
            description=self.description,
        )


class Tool(abc.ABC):
    """A tool that can be used by a model to generate replies."""

    name: str
    """The name of the tool."""
    description: str
    """A description of the tool."""
    parameters: list[ToolParameter]
    """A list of parameters for the tool."""

    @abc.abstractmethod
    def use(self, **kwargs) -> str:
        """Use the tool."""

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

    def _validate_args(self, **kwargs):
        """Validate the dictionary of keyword arguments."""
        required_params = [
            param.name for param in self.parameters if not param.optional
        ]

        if not all([param in kwargs for param in required_params]):
            raise ValueError("Missing required argument")
        if not all([param in self.parameters for param in kwargs]):
            raise ValueError("Invalid argument provided")


class ToolsManager:
    """Manager of tools available to a model."""

    def __init__(self, tools: list[Tool]) -> None:
        self.tools = tools
        """The tools available to the model."""

    @property
    def tools_dict(self) -> list[dict]:
        """The tools available to the model as a dictionary."""
        return [tool.to_dict() for tool in self.tools]

    def use(self, tool_name: str, **kwargs) -> str:
        """Execute a tool."""
        tool = self._get_tool(tool_name)
        return tool.use(**kwargs)

    def _get_tool(self, tool_name: str) -> Tool:
        """Get a tool by name."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        raise ValueError("Invalid tool name")


__all__ = ["Tool", "ToolsManager", "ToolParameter"]
