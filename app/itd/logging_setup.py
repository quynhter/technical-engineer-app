"""Журналы событий приложения и обращений к базе знаний."""
import logging
from logging.handlers import RotatingFileHandler


def configure(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name in ('db', 'ai'):
        logger = logging.getLogger(f'itd.{name}')
        if logger.handlers:
            continue
        handler = RotatingFileHandler(directory / f'{name}.log', maxBytes=2_000_000,
                                      backupCount=2, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
