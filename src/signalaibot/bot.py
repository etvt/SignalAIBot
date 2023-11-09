import logging
import os
import random
import tempfile

import asks
import feedparser
from bs4 import BeautifulSoup
from semaphore import Attachment, Bot, ChatContext


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
    async with Bot(os.environ["SIGNAL_PHONE_NUMBER"],
                   socket_path="/signald/signald.sock") as bot:
        # await bot.set_profile("[botee]", profile_about="", profile_avatar=str(Path.cwd() / "resources" / "avatar.jpg"))
        bot.register_handler("!ai", ai)
        bot.register_handler("!apod", apod)

        await bot.start()


async def start_with_reloader():
    from watchfiles import arun_process
    await arun_process(os.getcwd(), target=start_bot)


def main():
    import anyio

    if os.environ.get('RELOAD_ON_SOURCE_CHANGES', '').strip().lower() == "true":
        try:
            anyio.run(start_with_reloader)
        except ImportError:
            logging.error("watchfiles is not installed, cannot start with RELOAD_ON_SOURCE_CHANGES=True")
            anyio.run(start_bot)
    else:
        anyio.run(start_bot)


if __name__ == '__main__':
    main()
