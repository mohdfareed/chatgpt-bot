"""Utility and helper functions for the package."""

import html

import telegram
from chatgpt.chat_completion import ChatCompletion
from chatgpt.message import Reply
from telegram.constants import MessageEntityType, ParseMode
from telegram.ext import ExtBot


async def stream_message(model: ChatCompletion, bot: ExtBot, chat_history,
                         chat_id, topic_id=None) -> Reply:
    """Stream a message to the chat."""

    message = ''
    message_id = None
    chunk_size = 10
    counter = 0

    async def packet_handler(packet) -> None:
        nonlocal message, message_id, chunk_size, counter
        message += packet or ''
        counter += 1

        # send if enough chunks have been received
        if packet and counter % chunk_size != 0:
            return

        if not message_id:  # initial message to be appended
            if not topic_id:
                msg = await bot.send_message(chat_id=chat_id,
                                             text=html.escape(message),
                                             parse_mode=ParseMode.HTML)
            else:
                msg = await bot.send_message(chat_id=chat_id,
                                             text=html.escape(message),
                                             parse_mode=ParseMode.HTML,
                                             message_thread_id=topic_id)
            message_id = msg.message_id
        else:  # update the message
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                        text=html.escape(message),
                                        parse_mode=ParseMode.HTML)

        counter = 0
        return

    reply = await model.async_request(chat_history, packet_handler)
    model.cancel()  # cancel the request if it hasn't already finished
    return reply
