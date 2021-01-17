"""Init of weatherov module."""

from .weather import Weather
from .plotting import plot

from importlib.metadata import version

__version__ = version('weatho')
