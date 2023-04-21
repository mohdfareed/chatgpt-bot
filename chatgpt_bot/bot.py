"""The ChatGPT Telegram bot."""

from typing import AsyncGenerator, Callable

from qrcode import QRCode
from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import APPID, APPID_HASH, PASSPORT_KEY, TOKEN, session_path

qr = QRCode()


async def get_history(phone: str, user_id: int, chat_id: int,
                      auth_code: Callable[[], int] | int,
                      password: Callable[[], str] | str) -> AsyncGenerator:
    """Gets the chat history of a Telegram chat. Requires a Telegram account to
    launch a Telegram client. Sessions are saved in the config/sessions by the
    user ID of the Telegram account.

    Args:
        phone_num (str): The phone number of the Telegram account. It must
        include the country code.
        user_id (int): The user ID of the Telegram account.
        chat_id (int): The chat ID of the chat. The user must have access to
        the chat.
        auth_code (Callable | int): The code sent to the Telegram account. If a
        Callable is provided, it must return the code.
        password (Callable | str): The password of the Telegram account. If
        a Callable is provided, it must return the password.

    Returns:
        Iterable: The chat history.

    """

    def code_cmd() -> int:  # auth_code wrapper
        return auth_code() if callable(auth_code) else auth_code

    def password_cmd() -> str:  # password wrapper
        return password() if callable(password) else password

    # start the client
    print("starting telegram client...")
    session = session_path(str(user_id))
    client = TelegramClient(session, APPID, APPID_HASH)
    qr_code = QRCode()

    # authenticate the user
    if (not client.is_connected()):
        await client.connect()
    login_request = await client.qr_login()
    authorized = False
    while not authorized:
        qr_code.clear()
        qr_code.add_data(login_request.url)
        qr_code.print_ascii()
        try:
            authorized = await login_request.wait(10)
        except:
            await login_request.recreate()

    # await client.connect()
    # if not await client.is_user_authorized():
    #     print("authorizing user...")
    #     await client.send_code_request(phone)
    #     try:  # sign in
    #         await client.sign_in(phone, code_cmd())
    #     except SessionPasswordNeededError:
    #         await client.sign_in(password=password_cmd())

    # retrieve chat history
    async with client:
        async for message in client.iter_messages(chat_id, reverse=True):
            yield message


async def sync_history(update: Update, _):
    """Syncs the chat history of a Telegram chat with the database."""

    # read user credentials
    print("authenticating...")
    user_id = update.message.from_user.id
    phone = '+15855579439'
    # phone = await parse_passport(update, _)
    def code(): return int(input("Enter the code sent to your account: "))
    def password(): return 'MJ7rhefQC3lPUw#!'

    print("syncing chat history...")
    # retrieve chat history of the chat
    chat_id = update.message.chat_id
    # chat_id = "https://t.me/+VD0_If5KL35jYjk0"
    chat_history = get_history(phone, user_id, chat_id, code, password)
    # sync history
    i = 0
    async for message in chat_history:
        i += 1
        print(f"{message.sender_id}: {message.text}")
        if i == 5:
            break


async def parse_passport(update: Update, _):
    """Downloads and returns the phone number through a passport."""
    print("parsing passport data...")
    # retrieve passport data
    passport_data = update.message.passport_data
    # if the nonce doesn't match, the update did not originate from here
    if passport_data.decrypted_credentials.nonce != "thisisatest":
        print("invalid nonce received")
        return
    # parse the decrypted credential data
    for data in passport_data.decrypted_data:
        if data.type == "phone_number":
            return data.phone_number
        print("no phone number found in passport data")


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(update.effective_chat.id,  # type: ignore
                                   text="I'm a bot, please talk to me!")


async def sync_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(update.effective_chat.id,  # type: ignore
                                   text="Syncing chat history...")
    await sync_history(update, context)


def main():
    print("starting telegram bot...")
    app = Application.builder()
    app = app.token(TOKEN).private_key(PASSPORT_KEY).build()
    # add handlers
    app.add_handler(CommandHandler('start', start_cmd))
    app.add_handler(CommandHandler('sync', sync_cmd))
    app.add_handler(MessageHandler(filters.PASSPORT_DATA, sync_history))
    # start the bot
    app.run_polling()


def run():
    """Run the bot."""
    main()
    # asyncio.run(main())


if __name__ == '__main__':
    run()
