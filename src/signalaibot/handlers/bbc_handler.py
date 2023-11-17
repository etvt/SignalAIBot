import asks
import feedparser
from semaphore import ChatContext

from signalaibot.handlers.framework.handler_base import handler

FEEDS = {
    "world": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "politics": "http://feeds.bbci.co.uk/news/politics/rss.xml",
    "business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "tech": "http://feeds.bbci.co.uk/news/technology/rss.xml",
}

DEFAULT_FEED = "http://feeds.bbci.co.uk/news/rss.xml"


@handler(r"^!bbc(.*)")
async def bbc(ctx: ChatContext) -> None:
    try:
        news = ctx.match.group(1).strip()
    except IndexError:
        news = DEFAULT_FEED

    if news == "info":
        info = """BBC News Bot

    !bbc          - BBC News
    !bbc world    - BBC World News
    !bbc business - BBC Business News
    !bbc politics - BBC Politics News
    !bbc tech     - BBC Technology News"""
        await ctx.message.reply(body=info)
    else:
        requested_feed = FEEDS.get(news, DEFAULT_FEED)

        # Parse news feed.
        feed = feedparser.parse((await asks.get(requested_feed)).text)

        # Create message with 3 latest headlines.
        reply = []
        for x in range(3):
            pointer = feed.entries[x]
            reply.append(f"{pointer.title} ({pointer.link})")
            if x < 2:
                reply.append("\n")

        await ctx.message.reply("\n".join(reply))
