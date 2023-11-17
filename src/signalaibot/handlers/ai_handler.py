import random

from semaphore import ChatContext

from signalaibot.handlers.framework.handler_base import handler


@handler(r"^!ai")
async def ai(ctx: ChatContext) -> None:
    if 'known_receiver' in ctx.data:
        emoji = ['❤️', '🔥', '👍', '💩', '🐰']
        await ctx.message.reply(random.choice(emoji), reaction=True)
    else:
        ctx.data['known_receiver'] = True
        await ctx.message.reply('👋', reaction=True)
        await ctx.message.reply("Hi! I'm a Signal bot running in a Docker container!",
                                quote=False)
