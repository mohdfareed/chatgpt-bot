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
    message_id = None
    chunk_size = 10
    counter = 0

    async def packet_handler(packet: str | None) -> None:
        nonlocal message, message_id, chunk_size, counter
        message += packet or ''
        counter += 1

        # send if enough chunks have been received
        if packet and counter % chunk_size != 0:
            return

        if message_id is None:  # initial message to be appended
            msg = await bot.send_message(chat_id=chat_id, text=message)
            message_id = msg.message_id
        else:  # update the message
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                        text=message)
        if not packet and counter == 1:  # leftover message to be sent
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                        parse_mode=ParseMode.MARKDOWN_V2,
                                        text=message)

        counter = 0
        return

    reply = await model.async_request(chat_history, packet_handler)
    model.cancel()  # cancel the request if it hasn't already finished
    return reply
