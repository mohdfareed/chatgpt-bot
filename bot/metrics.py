"""Model usage metrics."""

import typing

import sqlalchemy as sql
import sqlalchemy.ext.asyncio as async_sql
import sqlalchemy.orm as orm
from typing_extensions import override

import chatgpt.core
import chatgpt.events
import database.core as database
from bot import core, utils


class ModelMetricsHandler(chatgpt.events.ToolUse, chatgpt.events.ModelReply):
    """Handles metrics of model generated replies."""

    def __init__(self, message: core.TelegramMessage):
        self.user_message = message
        """The user message to which the model is replying."""

    @override
    async def on_tool_use(self, usage):
        # count usage towards the user's metrics
        await utils.count_usage(self.user_message, usage)

    @override
    async def on_model_reply(self, reply):
        # count usage towards the user's metrics
        await utils.count_usage(self.user_message, reply)


class TelegramMetrics(database.DatabaseModel):
    """Telegram metrics."""

    __tablename__ = "telegram_metrics"

    entity_id: orm.Mapped[str] = orm.mapped_column(unique=True)
    """The entity's ID (i.e. chat ID or user ID)."""
    usage: orm.Mapped[int] = orm.mapped_column(default=0)
    """The entity's token usage count."""
    usage_cost: orm.Mapped[float] = orm.mapped_column(default=0.0)
    """The entity's token usage cost."""
    reply_to_mentions: orm.Mapped[bool] = orm.mapped_column(default=True)
    """Whether the entity prefers replies to mentions only or all messages."""
    data: orm.Mapped[str | None] = orm.mapped_column(database.encrypted_column)
    """The entity's configurations data."""

    @property
    def configs(self) -> list[str]:
        """The entity's model configs."""
        if self.data:
            return self.data.split("\n")
        else:
            return []

    @configs.setter
    def configs(self, configs: list[str]):
        self.data = "\n".join(configs)

    def __init__(
        self,
        id: int | None = None,
        entity_id: str | None = None,
        usage: int = 0,
        usage_cost: float = 0.0,
        configs: list[str] = [],
        engine: async_sql.AsyncEngine | None = None,
        **kw: typing.Any,
    ):
        super().__init__(
            id=id,
            entity_id=entity_id,
            usage=usage,
            usage_cost=usage_cost,
            configs=configs,
            engine=engine,
            **kw,
        )

    @property
    @override
    def _loading_statement(self):
        return sql.select(type(self)).where(
            (type(self).id == self.id)
            | (type(self).entity_id == self.entity_id)
        )

    @classmethod
    async def get_configs(cls, entity_id: str):
        """Get the configs used by an entity."""
        entity = await TelegramMetrics(entity_id=entity_id).load()
        # deserialize the configs
        return [
            chatgpt.core.ModelConfig.deserialize(c) for c in entity.configs
        ]

    @classmethod
    async def add_config(
        cls, entity_id: str, config: chatgpt.core.ModelConfig
    ):
        """Store a config used by an entity."""
        entity = await TelegramMetrics(entity_id=entity_id).load()
        # serialize the model and add it if it doesn't exist
        if (serialized_config := config.serialize()) not in entity.configs:
            entity.configs = entity.configs + [serialized_config]
            await entity.save()
            return True
        return False

    @classmethod
    async def delete_config(
        cls, entity_id: str, config: chatgpt.core.ModelConfig
    ):
        """Store a config used by an entity."""
        entity = await TelegramMetrics(entity_id=entity_id).load()
        try:  # remove the model from the entity's models
            configs = entity.configs
            configs.remove(config.serialize())
            entity.configs = configs

            await entity.save()
            return True
        except ValueError:
            return False
