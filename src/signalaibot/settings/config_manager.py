import logging
import os

from signalaibot.settings import constants
from signalaibot.settings.model import Config, Env


def load_config():
    env_dict = {}

    # env file
    env_file_path = constants.ENV_FILE_PATH
    if env_file_path and os.path.exists(env_file_path):
        logging.info("Loading config from .env file...")
        from .dotenv import dotenv_values
        env_dict.update(dotenv_values(env_file_path))

    # secret folder
    secrets_path = constants.SECRETS_PATH
    if secrets_path and os.path.exists(secrets_path):
        logging.info("Loading secrets from secrets path...")
        for filename in os.listdir(secrets_path):
            file_path = os.path.join(secrets_path, filename)
            if os.path.isfile(file_path) and os.path.getsize(file_path) <= constants.ONE_KB:
                with open(file_path, 'r') as file:
                    env_dict[filename] = file.read()

    # env vars
    logging.info("Loading environment variables...")
    env_dict.update(os.environ)
    return Config.from_env_dict(env_dict)


def load_env_and_config():
    global env
    global config

    logging.info("Loading environment and config...")

    env = Env.from_os_environ()
    logging.info(f"Environment is {env}")

    config = load_config()
    logging.info(f"Config loaded for {env}")


# ------- globals -------
env: Env
config: Config

load_env_and_config()
