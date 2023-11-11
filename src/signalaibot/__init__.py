import logging

logging.basicConfig(
    format='%(asctime)s %(threadName)s: [%(levelname)s] %(message)s',
    level=logging.INFO
)

from signalaibot.patches import semaphore_patches

semaphore_patches.apply()
