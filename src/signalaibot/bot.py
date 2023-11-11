import logging
import random
import signal
import tempfile

import anyio
import asks
import feedparser
from anyio import open_signal_receiver, CancelScope
from bs4 import BeautifulSoup
from semaphore import Attachment, Bot, ChatContext

from signalaibot.settings import state_manager
from signalaibot.settings.config_manager import config


async def ai(ctx: ChatContext) -> None:
    if 'known_receiver' in ctx.data:
        emoji = ['❤️', '🔥', '👍', '💩', '🐰']
        await ctx.message.reply(random.choice(emoji), reaction=True)
    else:
        ctx.data['known_receiver'] = True
        await ctx.message.reply('👋', reaction=True)
        await ctx.message.reply("Hi! I'm a Signal bot running in a Docker container!",
                                quote=False)


async def apod(ctx: ChatContext) -> None:
    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        path = temp_file.name
        content = (await asks.get('https://apod.nasa.gov/apod.rss')).text
        Feed = feedparser.parse(content)
        pointer = Feed.entries[0]
        soup = BeautifulSoup(pointer.description, "html.parser")

        for img in soup.find_all("img"):
            apod = img["src"]
            description = img["alt"]

        r = await asks.get(apod, stream=True)
        async with await anyio.open_file(path, "wb") as f:
            async for chunk in r.body:
                await f.write(chunk)

        message = f"{pointer.title} - {description} (https://apod.nasa.gov/apod/)"
        attachment = Attachment(str(path), width=100, height=100)

        await ctx.message.reply(body=message, attachments=[attachment])


async def start_bot():
    try:
        async with Bot(config.bot_username,
                       # profile_name="[botee]", profile_picture=str(Path.cwd() / "resources" / "avatar.jpg"),
                       group_auto_accept=False,
                       socket_path="/signald/signald.sock") as bot:
            async with anyio.create_task_group() as tg:
                tg.start_soon(interrupt_handler, tg.cancel_scope)
                logging.info("Registering handlers...")
                bot.register_handler("!ai", ai)
                bot.register_handler("!apod", apod)

                await bot.start()
    finally:
        state_manager.save_state()


async def interrupt_handler(cancel_scope: CancelScope):
    with open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        async for signum in signals:
            logging.warning(f"Received signal {signum} from system.")
            if signum == signal.SIGTERM or signum == signal.SIGINT:
                # noinspection PyAsyncCall
                cancel_scope.cancel()
                break
