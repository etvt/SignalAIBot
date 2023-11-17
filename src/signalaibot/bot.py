import logging
import signal

import anyio
from anyio import open_signal_receiver, CancelScope

from signalaibot.extensions.semaphore_extensions import ExtendedBot
from signalaibot.handlers import register_handlers_on_bot, load_handlers
from signalaibot.settings.config_manager import config
from signalaibot.settings.state_manager import state, StateSaveContext, state_save_context


async def start_bot():
    async with ExtendedBot(config.bot_number,
                           # profile_name="[botee]", profile_picture=str(Path.cwd() / "resources" / "avatar.jpg"),
                           group_auto_accept=False,
                           raise_errors=True,
                           socket_path="/signald/signald.sock") as bot:
        async with state_save_context() as save_context:
            async with anyio.create_task_group() as tg:
                tg.start_soon(interrupt_handler, tg.cancel_scope)

                await initialize_state(bot, save_context)

                logging.info("Loading handlers...")
                load_handlers()

                logging.info("Registering handlers...")
                register_handlers_on_bot(bot)

                await bot.start()
    logging.info("Bot exited...")


async def initialize_state(bot, save_context: StateSaveContext):
    if state.bot_uuid is None:
        state.bot_uuid = (await bot.get_address_from_number(config.bot_number)).uuid
        save_context.save_soon(state)
    logging.info(f"Bot uuid is: {state.bot_uuid}")

    if state.admin_uuid is None:
        state.admin_uuid = (await bot.get_address_from_number(config.admin_number)).uuid
        save_context.save_soon(state)
    logging.info(f"Admin uuid is: {state.admin_uuid}")


async def interrupt_handler(cancel_scope: CancelScope):
    with open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        async for signum in signals:
            logging.warning(f"Received signal {signum} from system.")
            if signum == signal.SIGTERM or signum == signal.SIGINT:
                # noinspection PyAsyncCall
                cancel_scope.cancel()
                break
