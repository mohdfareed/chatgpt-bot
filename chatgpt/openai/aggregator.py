"""Aggregate reply packets into a single model message reply."""

import chatgpt.core


class MessageAggregator:
    """Aggregates message chunks into a single message."""

    def __init__(self):
        self._is_aggregating = False
        self.content = ""
        self.tool_name = None
        self.args_str = None
        self.finish_reason = chatgpt.core.FinishReason.UNDEFINED

    def add(self, message: chatgpt.core.ModelMessage):
        self._is_aggregating = True
        self.content += message.content
        self.finish_reason = message.finish_reason
        if isinstance(message, chatgpt.core.ToolUsage):
            self.tool_name = (self.tool_name or "") + message.tool_name
            self.args_str = (self.args_str or "") + message.args_str

    @property
    def reply(self):
        if not self._is_aggregating:
            return None  # no messages received

        # create reply from aggregated messages
        if self.tool_name or self.args_str:
            reply = chatgpt.core.ToolUsage(
                self.tool_name or "", self.args_str or "", self.content
            )
        else:  # normal message
            reply = chatgpt.core.ModelMessage(self.content)

        reply.finish_reason = self.finish_reason
        return reply
