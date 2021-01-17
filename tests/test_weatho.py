""" Tests for the weatho module. Run with pytest"""

from pathlib import Path
from datetime import datetime, timedelta
import pytz

import weatho
from weatho.locations import coordinates

modulefolder = Path(weatho.__file__).parent / '..'
datafolder = modulefolder / 'data'

Lyon = coordinates['Lyon']

cet = pytz.timezone('Europe/Paris')
utc = pytz.utc

w_ds = weatho.Weather(Lyon, source='darksky')  # DarkSky API
w_ow = weatho.Weather(Lyon, source='owm')      # OpenWeatherMap API

date_cet_1 = cet.localize(datetime(2021, 1, 10))
date_cet_2 = cet.localize(datetime(2021, 1, 14))

date_utc_1 = utc.localize(datetime(2021, 1, 12))
date_utc_2 = utc.localize(datetime(2021, 1, 16))


def midnight_of_day(date, source):
    """Return 00:00 of the current date:
    - In CET time if source == 'darksky'
    - In UTC time if source == 'owm'
    """
    tz = cet if source == 'darksky' else utc
    d = date.astimezone(tz)
    year, month, day = d.year, d.month, d.day
    return tz.localize(datetime(year, month, day))


def test_load_darksky():
    """Load data stored in a folder, initially downloaded from Darksky API.

    Returned data is in raw, source-dependent format.
    With DarkSky, hourly data goes from 00:00 to 23:00 in local time
    """
    date = date_cet_2
    data = w_ds.load(date, path=datafolder)

    t0_hourly = data['hourly']['data'][0]['time']
    t_midnight = midnight_of_day(date, source='darksky').timestamp()

    assert t0_hourly == t_midnight


def test_load_owm():
    """Load data stored in a folder, initially downloaded from OpenWeatherMap API.

    Returned data is in raw, source-dependent format.
    With DarkSky, hourly data goes from 00:00 to 23:00 in UTC time
    """
    date = date_cet_2
    data = w_ow.load(date, path=datafolder)

    t0_hourly = data['hourly'][0]['dt']
    t_midnight = midnight_of_day(date, source='owm').timestamp()

    assert t0_hourly == t_midnight


date = date_cet_1
ndays = 7


def test_hourly_ndays():
    """Load hourly data of several days, using the ndays argument. Here, DarkSky.

    Returned data is formatted, source-independent data.
    """
    data = w_ds.hourly(date, path=datafolder, ndays=ndays)
    assert len(data['T']) == ndays * 24
    assert type(data['T'][-1]) is float


def test_missing_days_ndays():
    """Find missing days, using the ndays argument, with DarkSky data"""
    mdays = w_ds.missing_days(date, path=datafolder, ndays=ndays + 2, verbose=False)
    assert len(mdays) == 2


date1 = date_utc_1
date2 = date_utc_2


def test_hourly_until():
    """Load hourly data of several days, using the ndays argument. Here, DarkSky.

    Returned data is formatted, source-independent data.
    """
    ndays = (date2 - date1).days + 1
    data = w_ow.hourly(date1, path=datafolder, until=date2)
    assert len(data['T']) == ndays * 24
    assert type(data['T'][-1]) is float


def test_missing_days_until():
    """Find missing days, using the until argument, with OWM data."""
    date0 = date1 - timedelta(days=2)
    date3 = date2 + timedelta(days=2)
    mdays = w_ow.missing_days(date0, path=datafolder, until=date3, verbose=False)
    assert len(mdays) == 4


def test_plot():
    """Test plotting of hourly data."""
    data = w_ds.hourly(date=date_cet_1, path=datafolder, until=date_cet_2)
    weatho.plot(data)
    assert True  # is evaluated once the figure is closed
