import logging
import os

import anyio
from watchfiles import run_process

from signalaibot import bot

logging.basicConfig(
    format='%(asctime)s %(threadName)s: [%(levelname)s] %(message)s',
    level=logging.INFO
)


def start_bot():
    logging.info("Starting bot...")
    anyio.run(bot.start_bot)


def start(with_reloader: bool = False):
    if with_reloader:
        logging.info("Starting bot with source code reloader...")
        try:
            from watchfiles import arun_process
            run_process(os.getcwd(), target=start_bot)
        except ImportError:
            logging.error("watchfiles is not installed, cannot start bot with source code reloader!")
            start_bot()
    else:
        start_bot()


def main():
    with_reloader = os.environ.get('RELOAD_ON_SOURCE_CHANGES', '').strip().lower() == "true"
    start(with_reloader)


if __name__ == '__main__':
    main()
