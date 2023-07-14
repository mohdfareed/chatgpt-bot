"""Aggregate reply packets into a single model message reply."""

from chatgpt import core, messages


class MessageAggregator:
    """Aggregates message chunks into a single message."""

    def __init__(self):
        self.content = ""
        self.tool_name = ""
        self.args_str = ""
        self.finish_reason = core.FinishReason.UNDEFINED

    def add(self, message: messages.ModelMessage):
        self.content += message.content
        if isinstance(message, messages.ToolUsage):
            self.tool_name += message.tool_name
            self.args_str += message.args_str
        self.finish_reason = message.finish_reason

    @property
    def reply(self):
        # create reply from aggregated messages
        if self.tool_name or self.args_str:
            reply = messages.ToolUsage(
                self.tool_name, self.args_str, self.content
            )
        else:  # normal message
            reply = messages.ModelMessage(self.content)

        reply.finish_reason = self.finish_reason
        return reply
