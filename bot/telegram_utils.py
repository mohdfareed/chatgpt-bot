"""Telegram related utilities."""

import asyncio

import telegram.constants

from bot import core, formatter

TYPING_STATUS = telegram.constants.ChatAction.TYPING
PARSE_MODE = telegram.constants.ParseMode.HTML


async def send_message(
    message: core.TelegramMessage, new_message: str, markup=None
):
    """Send a new message to the chat of a message."""
    new_message = formatter.format_message(new_message)
    msg = await message.telegram_message.chat.send_message(
        new_message,
        PARSE_MODE,
        reply_markup=markup,  # type: ignore
        message_thread_id=message.topic_id,  # type: ignore
    )
    return core.TelegramMessage(msg)


async def edit_message(
    message: core.TelegramMessage, new_message: str, markup=None
):
    """Edit a message with the new message."""
    new_message = formatter.format_message(new_message)
    try:  # try to edit the existing reply
        msg = await message.telegram_message.edit_text(
            new_message, PARSE_MODE, reply_markup=markup  # type: ignore
        )
        if type(msg) == bool:
            msg = message.telegram_message
        return core.TelegramMessage(msg)
    except telegram.error.BadRequest as e:
        if "Message is not modified" in str(e):
            return message  # ignore if the message was not modified
        else:  # raise if the error is not due to the message not changing
            raise e


async def reply(message: core.TelegramMessage, new_message: str, markup=None):
    """Reply to a message with a new message."""
    new_message = formatter.format_message(new_message)
    msg = await message.telegram_message.reply_html(
        new_message,
        reply_markup=markup,  # type: ignore
    )
    return core.TelegramMessage(msg)


async def reply_code(
    message: core.TelegramMessage, reply_text: str, markup=None
):
    """Reply to a message with a code block."""
    return await reply(message, f"<code>{reply_text}</code>", markup)


def set_typing_status(message: core.TelegramMessage):
    """Set the typing status of the message's chat."""

    async def _set_status():
        while True:
            await message.telegram_message.chat.send_action(TYPING_STATUS)
            await asyncio.sleep(5)

    return asyncio.create_task(_set_status())


def create_markup(
    buttons: list[list[core.Button]],
) -> telegram.InlineKeyboardMarkup:
    markup = []
    for row in buttons:
        markup += [[button.telegram_button for button in row]]
    return telegram.InlineKeyboardMarkup(markup)
