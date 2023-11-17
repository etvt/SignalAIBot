import logging
from functools import wraps
from re import Pattern
from typing import Callable, Tuple

from semaphore import ChatContext

from signalaibot.handlers import add_handler
from signalaibot.settings.model import Role, ConversationType, RequestContext


def handler(regex: str | Pattern,
            minimum_role: Role = Role.USER,
            allowed_conversation_types: Tuple[ConversationType, ...] = (
                    ConversationType.PRIVATE, ConversationType.GROUP),
            priority: int = 100):
    def wrapper(original_handler: Callable):
        handler_name = original_handler.__name__

        @wraps(original_handler)
        def new_handler(ctx: ChatContext):
            request_context: RequestContext = ctx.data['request_context']

            if request_context.conversation.type in allowed_conversation_types:
                if request_context.sender_role_in_conversation.access_level >= minimum_role.access_level:
                    logging.info(f"----> Executing handler '{handler_name}' for sender {request_context.sender}.")
                    return original_handler(ctx)
                else:
                    logging.warning(f"Sender {request_context.sender} from {request_context.conversation} tried"
                                    f" to use {handler_name} but they are not entitled to!")
                    return do_nothing()
            else:
                logging.warning(f"Sender {request_context.sender} from {request_context.conversation} tried"
                                f" to use {handler_name} which is not allowed for this conversation type!")
                return do_nothing()

        add_handler(regex, new_handler, priority)
        return new_handler

    return wrapper


def root_handler(regex: str | Pattern,
                 priority: int = 0):
    def wrapper(original_handler: Callable):
        handler_name = original_handler.__name__

        @wraps(original_handler)
        def new_handler(ctx: ChatContext):
            logging.info(f"----> Executing root handler '{handler_name}' for sender {ctx.message.source.uuid}.")
            return original_handler(ctx)

        add_handler(regex, new_handler, priority)
        return new_handler

    return wrapper


async def do_nothing():
    pass
