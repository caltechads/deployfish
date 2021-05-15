from pathlib import Path

from jinja2 import FileSystemLoader, Environment

__version__ = "0.30.17"

TEMPLATE_PATHS = [
    Path(__file__).parent / 'cli' / 'templates'
]

jinja_env = Environment(loader=FileSystemLoader([str(p) for p in TEMPLATE_PATHS]))
