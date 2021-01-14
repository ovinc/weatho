"""Init of weatherov module."""

from .weather import Weather, plot

from importlib.metadata import version

__version__ = version('weatherov')
