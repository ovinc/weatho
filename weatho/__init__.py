"""Init of weatherov module."""

from .weather import Weather
from .plotting import plot

# from importlib.metadata import version  # only for python 3.8+
from importlib_metadata import version

__version__ = version('weatho')
__author__ = 'Olivier Vincent'
__license__ = '3-Clause BSD'
