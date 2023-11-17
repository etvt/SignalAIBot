import fnmatch
import importlib
import inspect
import os
from re import Pattern
from typing import Callable, Tuple, List

from semaphore import Bot

handlers: List[Tuple[str | Pattern, Callable, int]] = []


def load_handlers():
    package_name = __name__
    load_handlers_from(f"{package_name}.framework")
    load_handlers_from(f"{package_name}")


def load_handlers_from(full_package_name: str):
    package_dir = get_package_dir(full_package_name)
    for filename in os.listdir(package_dir):
        if fnmatch.fnmatch(filename, '*_handler.py'):
            full_module_name = f"{full_package_name}.{filename[:-3]}"  # Remove '.py' and append to package name
            importlib.import_module(full_module_name)


def get_package_dir(package_name: str):
    module = importlib.import_module(package_name)
    module_path = inspect.getfile(module)
    return os.path.dirname(module_path)


def add_handler(regex: str | Pattern, handler: Callable, priority: int):
    handlers.append((regex, handler, priority))


def register_handlers_on_bot(bot: Bot):
    for (regex, handler, _) in sorted(handlers, key=lambda e: e[2]):
        bot.register_handler(regex, handler)
