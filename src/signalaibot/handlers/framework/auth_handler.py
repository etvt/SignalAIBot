import logging
from typing import cast

from aiocache import cached
from anyio import get_cancelled_exc_class
from semaphore import ChatContext, StopPropagation, Message

from signalaibot.extensions.semaphore_extensions import ExtendedBot
from signalaibot.handlers.framework.handler_base import Role, ConversationType, root_handler
from signalaibot.settings.model import ConversationMeta, Conversation, RequestContext
from signalaibot.settings.state_manager import state, state_save_context, StateSaveContext


@root_handler("",
              priority=0)
async def auth(chat_context: ChatContext) -> None:
    try:
        sender, conversation = await extract_sender_and_conversation(chat_context)

        async with state_save_context() as save_context:
            if is_removal_from_group(conversation.type, chat_context):
                await handle_removal_from_group(conversation, save_context)
            else:
                await handle_message_or_invite(sender, conversation, chat_context, save_context)
    except get_cancelled_exc_class():
        raise
    except StopPropagation:
        raise
    except Exception as ex:
        error = "Exception occurred in auth handler, stopping propagation for safety!\n" \
                f"Exception: {ex}"
        logging.error(error)
        raise StopPropagation(error)


async def extract_sender_and_conversation(chat_context: ChatContext):
    sender = chat_context.message.source.uuid
    assert sender, "Sender uuid is not set!"

    group_id = chat_context.message.get_group_id()
    conversation_type = ConversationType.GROUP if group_id else ConversationType.PRIVATE

    conversation = Conversation(type=conversation_type,
                                id=sender if conversation_type == ConversationType.PRIVATE else group_id)
    return sender, conversation


async def handle_message_or_invite(sender: str, conversation: Conversation,
                                   chat_context: ChatContext, save_context: StateSaveContext):
    request_context = RequestContext(sender=sender, conversation=conversation)
    chat_context.data['request_context'] = request_context

    sender_role_in_conversation = get_assigned_role(sender, conversation)
    request_context.sender_role_in_conversation = sender_role_in_conversation

    logging.info(f"Authorization check for sender {sender} from conversation {conversation} resulted in"
                 f" role: {sender_role_in_conversation}.")

    if sender_role_in_conversation == Role.REJECTED:
        error = f"Sender {sender} from conversation {conversation} was rejected access to the bot!"
        logging.error(error)
        # TODO leave the group again
        raise StopPropagation(error)
    elif sender_role_in_conversation == Role.NONE:
        error = f"Sender {sender} from conversation {conversation} is unauthorized to access the bot!"
        if conversation not in state.requested_conversations:
            logging.error(error)
            logging.info(f"Requesting approval for {sender} from conversation {conversation} by admin...")

            conversation_meta = ConversationMeta(request_id=state.request_id_next_value)
            state.request_id_next_value += 1
            state.requested_conversations[conversation] = conversation_meta
            save_context.save_soon(state)

            await send_request_to_admin(conversation, conversation_meta, chat_context)

        raise StopPropagation(error)
    elif sender_role_in_conversation in (Role.USER, Role.ADMIN):
        logging.info(f"Sender {sender} from conversation {conversation} is authorized to access the bot!")
        if sender_role_in_conversation == Role.ADMIN and conversation not in state.authorized_conversations:
            logging.info(f"The admin interacted from {conversation},"
                         f" which will be automatically added as an authorized conversation!")
            state.authorized_conversations.add(conversation)
            save_context.save_soon(state)
        return
    else:
        error = f"Unhandled role {sender_role_in_conversation}!"
        logging.error(error)
        raise StopPropagation(error)


async def handle_removal_from_group(conversation: Conversation, save_context: StateSaveContext):
    logging.info(f"Bot removed from group {conversation}, cleaning up the state file...")

    if conversation in state.requested_conversations:
        state.requested_conversations.pop(conversation)
        save_context.save_soon(state)

    if conversation in state.authorized_conversations:
        state.authorized_conversations.remove(conversation)
        save_context.save_soon(state)


def is_removal_from_group(conversation_type: ConversationType, chat_context: ChatContext):
    return (conversation_type == ConversationType.GROUP
            and chat_context.message.data_message
            and chat_context.message.data_message.groupV2
            and chat_context.message.data_message.groupV2.removed is True)


def get_assigned_role(sender: str, conversation: Conversation) -> Role:
    if sender == state.admin_uuid:
        return Role.ADMIN

    if conversation in state.rejected_conversations:
        return Role.REJECTED

    if conversation in state.authorized_conversations:
        return Role.USER

    return Role.NONE


async def send_request_to_admin(conversation: Conversation,
                                conversation_meta: ConversationMeta,
                                chat_context: ChatContext):
    try:
        sender_name = await get_sender_name(chat_context.message)
        if not sender_name:
            sender_name = "<unknown>"

        conversation_title = None
        if conversation.type == ConversationType.GROUP:
            conversation_title = await get_group_title(chat_context)
        if not conversation_title:
            conversation_title = sender_name

        request_message = (
            f"The sender '{sender_name}' with number '{chat_context.message.source.number or '<unknown>'}'"
            f" from {conversation.type.value} conversation '{conversation_title}'"
            f" is requesting access to the bot!\n")

        incoming_message = chat_context.message.get_body()
        if incoming_message:
            request_message += f"First message of the sender is: {incoming_message}\n"

        request_message += (f"To approve/reject the handling of messages coming from this conversation"
                            f" please use the following command: !adm req {conversation_meta.request_id} y/n.")

        sent = await chat_context.bot.send_message(state.admin_uuid, request_message)
        if not sent:
            raise AssertionError(f"Unable to send approval request for conversation {conversation} to the admin!")
    except get_cancelled_exc_class():
        raise
    except Exception:
        logging.error(f"Unable to send approval request for conversation {conversation} to the admin!")
        raise


def key_builder_get_sender_name(func, msg: Message):
    return msg.source.uuid


@cached(key_builder=key_builder_get_sender_name)
async def get_sender_name(msg: Message) -> str:
    sender_name = None

    try:
        sender_profile = await msg.get_profile()
        if sender_profile:
            sender_name = sender_profile.name
    except get_cancelled_exc_class():
        raise
    except Exception:
        logging.error(f"Could not fetch profile info for {msg.source.uuid}!")

    return sender_name


def key_builder_get_group_title(func, chat_context: ChatContext):
    return chat_context.message.get_group_id()


@cached(key_builder=key_builder_get_group_title)
async def get_group_title(chat_context: ChatContext) -> str:
    group_title = None

    group_id = chat_context.message.get_group_id()
    try:
        bot = cast(ExtendedBot, chat_context.bot)
        group = await bot.get_group(group_id)
        if group and group.title:
            group_title = group.title
    except get_cancelled_exc_class():
        raise
    except Exception:
        logging.error(f"Could not fetch group title for id {group_id}!")

    return group_title
