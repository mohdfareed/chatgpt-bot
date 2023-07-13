"""Aggregate reply packets into a single model message reply."""

from chatgpt import core, messages


class MessageAggregator:
    """Aggregates message chunks into a single message."""

    def __init__(self):
        self._is_aggregating = False
        self.content = ""
        self.tool_name = ""
        self.args_str = ""
        self.finish_reason = core.FinishReason.UNDEFINED

    def add(self, message: messages.ModelMessage):
        self._is_aggregating = True
        self.content += message.content
        if isinstance(message, messages.ToolUsage):
            self.tool_name += message.tool_name
            self.args_str += message.args_str
        self.finish_reason = message.finish_reason

    @property
    def reply(self):
        if not self._is_aggregating:
            return None  # no messages received

        # create reply from aggregated messages
        if self.tool_name or self.args_str:
            reply = messages.ToolUsage(
                self.tool_name, self.args_str, self.content
            )
        else:  # normal message
            reply = messages.ModelMessage(self.content)

        reply.finish_reason = self.finish_reason
        return reply
