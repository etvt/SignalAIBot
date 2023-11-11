import logging
import os
from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic_core._pydantic_core import ValidationError


class Const:
    ENV_KEY = 'ENV'

    SECRETS_PATH = '/secrets/'
    ENV_FILE_PATH = '/persistent_data/.env'
    STATE_FILE_PATH = '/persistent_data/signalaibot_state.yaml'

    ONE_KB = 1024


class Env(Enum):
    PROD = 'PROD'
    DEV = 'DEV'
    DEFAULT = PROD

    @staticmethod
    def from_string(value: str) -> 'Env':
        return Env[value]

    @staticmethod
    def from_os_environ() -> 'Env':
        given = os.environ.get(Const.ENV_KEY, None)
        return Env.from_string(given) if given else Env.DEFAULT


class Config(BaseModel):
    bot_username: str
    admin_username: str

    openai_api_key: str

    @staticmethod
    def from_env_dict(source_env_dict: dict[str, Any]) -> 'Config':
        lower_case_dict = {key.lower(): value for key, value in source_env_dict.items()}
        try:
            res = Config(**lower_case_dict)
        except ValidationError as ve:
            # extracting only some error details to hide potentially sensitive input
            raise ValueError(str(ve.errors(include_url=False, include_context=False, include_input=False))) from None
        return res


def load_config():
    env_dict = {}

    # env file
    env_file_path = Const.ENV_FILE_PATH
    if env_file_path and os.path.exists(env_file_path):
        logging.info("Loading config from .env file...")
        from .dotenv import dotenv_values
        env_dict.update(dotenv_values(env_file_path))

    # secret folder
    secrets_path = Const.SECRETS_PATH
    if secrets_path and os.path.exists(secrets_path):
        logging.info("Loading secrets from secrets path...")
        for filename in os.listdir(secrets_path):
            file_path = os.path.join(secrets_path, filename)
            if os.path.isfile(file_path) and os.path.getsize(file_path) <= Const.ONE_KB:
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
