"""Init of weatherov module."""

from .weather import Weather, weather_plot

from importlib.metadata import version

__version__ = version('weatherov')
