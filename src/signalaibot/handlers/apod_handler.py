import tempfile

import anyio
import asks
import feedparser
from bs4 import BeautifulSoup
from semaphore import ChatContext, Attachment

from signalaibot.handlers.framework.handler_base import handler


@handler(r"^!apod")
async def apod(ctx: ChatContext) -> None:
    with tempfile.NamedTemporaryFile(delete=True, suffix=".png") as temp_file:
        path = temp_file.name
        content = (await asks.get('https://apod.nasa.gov/apod.rss')).text
        feed = feedparser.parse(content)
        pointer = feed.entries[0]
        soup = BeautifulSoup(pointer.description, "html.parser")

        for img in soup.find_all("img"):
            apod = img["src"]
            description = img["alt"]

        r = await asks.get(apod, stream=True)
        async with await anyio.open_file(path, "wb") as f:
            async for chunk in r.body:
                await f.write(chunk)

        message = f"{pointer.title} - {description} https://apod.nasa.gov/apod"
        attachment = Attachment(str(path), width=100, height=100)

        await ctx.message.reply(body=message, attachments=[attachment])
