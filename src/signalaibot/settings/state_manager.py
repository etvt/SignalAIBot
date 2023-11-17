import contextlib
import logging
import os

import anyio
import yaml
from anyio import get_cancelled_exc_class
from anyio.abc import TaskGroup

from signalaibot.settings import constants
from signalaibot.settings.model import State


def load_state():
    global state

    yaml_file_path = constants.STATE_FILE_PATH
    if os.path.exists(yaml_file_path):
        state_dict = load_from_yaml(yaml_file_path)
        state = State.model_validate(state_dict)
    else:
        state = State()


def load_from_yaml(yaml_file_path: str) -> dict:
    logging.info(f"Loading bot state from file {yaml_file_path}...")
    with open(yaml_file_path, 'r') as file:
        data = yaml.safe_load(file) or {}
        return data


def save_state():
    global state

    yaml_file_path = constants.STATE_FILE_PATH
    save_to_yaml(yaml_file_path, state.to_json_dict())


def save_state_dict(state_dict):
    yaml_file_path = constants.STATE_FILE_PATH
    save_to_yaml(yaml_file_path, state_dict)


def save_to_yaml(yaml_file_path, state_dict):
    logging.info(f"Saving bot state to file {yaml_file_path}...")
    with open(yaml_file_path, 'w') as file:
        yaml.dump(state_dict, file, sort_keys=False)


class StateSaveContext:
    def __init__(self, task_group: TaskGroup, cooldown_seconds: int):
        self._task_group = task_group
        self._cooldown_seconds = cooldown_seconds
        self._save_running = False
        self._last_state_json = None

    def save_soon(self, st: State):
        self._last_state_json = st.to_json_dict()

        if not self._save_running:

            async def cooldown_then_save():
                try:
                    await anyio.sleep(self._cooldown_seconds)
                    logging.info("Cooldown finished. Proceeding with save...")

                    current_request = self._last_state_json
                    self._last_state_json = None
                    await anyio.to_thread.run_sync(save_state_dict, current_request)
                except get_cancelled_exc_class():
                    self._save_running = False
                    logging.info("Save cancelled (task cancelled)...")
                    if self._last_state_json is not None:
                        logging.info("Saving in a blocking way before exit...")
                        save_state_dict(self._last_state_json)  # blocking save, otherwise it will be cancelled again
                        logging.info("Save in a blocking way successful.")
                    raise
                else:
                    self._save_running = False
                    logging.info("Save successful.")
                    if self._last_state_json is not None:
                        self._save_running = True
                        logging.info("Save requested. Starting cooldown...")
                        self._task_group.start_soon(cooldown_then_save)

            self._save_running = True
            logging.info("Save requested. Starting cooldown...")
            self._task_group.start_soon(cooldown_then_save)
        else:
            logging.info("Save requested, but a save event is already scheduled. Skipping.")


_singleton_state_save_context: StateSaveContext | None = None


@contextlib.asynccontextmanager
async def state_save_context(cooldown_seconds: int = 5) -> StateSaveContext:
    global _singleton_state_save_context

    if _singleton_state_save_context is not None:
        logging.info("Nested save context: entering...")
        try:
            yield _singleton_state_save_context
        finally:
            logging.info("Nested save context: exiting...")  # note: save will be handled by the root context
    else:
        logging.info("Root save context: entering...")
        async with anyio.create_task_group() as tg:
            _singleton_state_save_context = StateSaveContext(tg, cooldown_seconds)
            try:
                yield _singleton_state_save_context
            finally:
                logging.info("Root save context: exiting...")
                # cancel running tasks (i.e. the save cooldown process)
                await tg.cancel_scope.cancel()
                _singleton_state_save_context = None


# ------- globals -------
state: State

load_state()
