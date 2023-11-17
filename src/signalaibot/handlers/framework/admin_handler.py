import logging
import os
import re
import signal

from semaphore import ChatContext

from signalaibot.handlers.framework.handler_base import handler
from signalaibot.settings.model import Role, ConversationType, Conversation, ConversationMeta
from signalaibot.settings.state_manager import state, state_save_context


@handler(r"^!adm\s+(\w+)\s*(.*)",
         minimum_role=Role.ADMIN,
         allowed_conversation_types=(ConversationType.PRIVATE,))
async def adm(ctx: ChatContext) -> None:
    subcommand = ctx.match.group(1)
    parameters = ctx.match.group(2)

    if subcommand == "req":
        req_params = re.search(r"(\d+)\s+([yn])", parameters)
        if req_params:
            request_id = int(req_params.group(1))
            choice = req_params.group(2)

            conversation, metadata = find_request_id(request_id)
            if conversation:
                async with state_save_context() as save_context:
                    if choice == 'y':
                        if conversation.type == ConversationType.GROUP:
                            await ctx.bot.accept_invitation(conversation.id)
                        state.requested_conversations.pop(conversation)
                        state.authorized_conversations.add(conversation)
                        save_context.save_soon(state)
                        logging.info(f"The admin approved the conversation {conversation}"
                                     f" with request id {metadata.request_id}.")
                        await ctx.message.reply("Request approved!")
                    elif choice == 'n':
                        state.requested_conversations.pop(conversation)
                        state.rejected_conversations.add(conversation)
                        save_context.save_soon(state)
                        logging.info(f"The admin rejected the conversation {conversation}"
                                     f" with request id {metadata.request_id}.")
                        await ctx.message.reply("Request rejected!")
                    else:
                        raise ValueError(f"Invalid req command parameter: '{choice}'!")
            else:
                await ctx.message.reply("Given request id not found!")
        else:
            await ctx.message.reply("Syntax error in the req command!")
    elif subcommand == "stop":
        logging.warning("The admin requested to stop the bot! This might result in the container"
                        " being restarted by the runtime.")
        await ctx.message.reply("Stopping bot! This might result in the automatic restart of the bot"
                                " by the runtime.")
        os.kill(os.getpid(), signal.SIGTERM)  # TODO be more elegant using the bot's cancel_scope
    elif subcommand == "zombie":
        logging.warning("The admin requested to zombie the bot! Removing all handlers!"
                        " Please restart the container to make it functional again.")
        await ctx.message.reply("Zombieing the bot! Restart the container to make it functional again.")
        ctx.bot._handlers = []
        logging.info("Removed handlers from bot.")
    else:
        await ctx.message.reply(f"Unknown subcommand {subcommand}!")


def find_request_id(request_id) -> (Conversation, ConversationMeta):
    return next(((conv, conv_meta)
                 for conv, conv_meta in state.requested_conversations.items()
                 if conv_meta.request_id == request_id),
                None)
