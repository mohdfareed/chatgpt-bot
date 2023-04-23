"""Utility and helper functions for the package."""

import asyncio

import telegram
from chatgpt.chat_completion import ChatCompletion
from chatgpt.message import Reply
from telegram.constants import MessageEntityType, ParseMode
from telegram.ext import ExtBot


async def stream_message(model: ChatCompletion, bot: ExtBot,
                         chat_id, chat_history) -> Reply:
    """Stream a message to the chat."""

    message = ''
    message_id = -1
    chunk_size = 10
    counter = 0

    async def packet_handler(packet: str | None) -> None:
        nonlocal message, message_id, chunk_size, counter
        message += packet or ''
        counter += 1

        # send if enough chunks have been received
        if packet and counter % chunk_size != 0:
            return

        if message_id < 0:  # initial message to be appended
            msg = await bot.send_message(chat_id=chat_id, text=message)
            message_id = msg.message_id
        else:  # update the message
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                        text=message)
        if not packet:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                        text=message)

        counter = 0
        return

    return await model.async_request(chat_history, packet_handler)
