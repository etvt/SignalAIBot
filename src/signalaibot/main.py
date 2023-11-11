import logging
import os

import anyio


def start_bot():
    logging.info("Starting bot...")
    from signalaibot import bot
    anyio.run(bot.start_bot)


def start(with_reloader: bool = False):
    if with_reloader:
        logging.info("Starting bot with source code reloader...")
        try:
            from watchfiles import run_process
            run_process(os.getcwd(), target=start_bot)
        except ImportError:
            logging.error("watchfiles is not installed, cannot start bot with source code reloader!")
            start_bot()
    else:
        start_bot()


def main():
    start(os.environ.get('RELOAD_ON_CODE_CHANGES', '').strip().lower() == "true")


if __name__ == '__main__':
    main()
