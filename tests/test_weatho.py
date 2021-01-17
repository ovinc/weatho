""" Tests for the weatho module. Run with pytest"""

from pathlib import Path
from datetime import datetime, timedelta
from pytz import timezone

import weatho
from weatho.locations import coordinates

modulefolder = Path(weatho.__file__).parent / '..'
datafolder = modulefolder / 'data'

Lyon = coordinates['Lyon']
tz = timezone('Europe/Paris')

w_ds = weatho.Weather(Lyon, source='darksky')  # DarkSky API
w_ow = weatho.Weather(Lyon, source='owm')      # OpenWeatherMap API

date0 = tz.localize(datetime(2021, 1, 10))
date1 = tz.localize(datetime(2021, 1, 14))


def test_load_darksky():
    """Load data stored in a folder, initially downloaded from Darksky API.

    Returned data is in raw, source-dependent format.
    """
    date = date1
    data = w_ds.load(date, path=datafolder)
    t = data['hourly']['data'][0]['time']
    assert t == date.timestamp()


def test_load_owm():
    """Load data stored in a folder, initially downloaded from OpenWeatherMap API.

    Returned data is in raw, source-dependent format.
    """
    date = date1
    data = w_ow.load(date, path=datafolder)
    t = data['hourly'][0]['dt']

    # For some reason, OWM data starts at 1am instead of midnight
    assert t == (date + timedelta(hours=1)).timestamp()


def test_hourly_ndays():
    """Load hourly data of several days, using the ndays argument. Here, DarkSky.

    Returned data is formatted, source-independent data.
    """
    date = date0
    ndays = 7
    data = w_ds.hourly(date, path=datafolder, ndays=ndays)
    assert len(data['T']) == ndays * 24



