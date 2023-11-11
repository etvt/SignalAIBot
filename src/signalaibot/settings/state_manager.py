import logging
import os
from typing import List, Dict

import yaml
from pydantic import BaseModel

from signalaibot.settings.config_manager import Const


class State(BaseModel):
    conversations: Dict[str, str] = {}  # conversation id (username or group id) -> user display name / group name
    conversation_requests: List[str] = []  # conversation id
    allowed_conversations: List[str] = []  # conversation id

    @classmethod
    def load_from_file(cls, yaml_file_path: str) -> 'State':
        with open(yaml_file_path, 'r') as file:
            data = yaml.safe_load(file) or {}
            return cls(**data)

    def save_to_file(self, yaml_file_path: str):
        with open(yaml_file_path, 'w') as file:
            yaml.dump(self.dict(), file)


def load_state():
    global state

    yaml_file_path = Const.STATE_FILE_PATH
    if os.path.exists(yaml_file_path):
        logging.info(f"Loading bot state from file {yaml_file_path}...")
        state = State.load_from_file(yaml_file_path)
    else:
        state = State()


def save_state():
    global state
    yaml_file_path = Const.STATE_FILE_PATH
    logging.info(f"Saving bot state to file {yaml_file_path}...")
    state.save_to_file(yaml_file_path)


# ------- globals -------
state: State

load_state()
