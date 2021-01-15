""" Download, analyze and plot weather data DarkSky or OpenWeatherMap API"""

# TODO: move from threading to concurrent futures?
# TODO: timezone management

# Standard Library
from datetime import datetime, timedelta
import threading
import time
import json
from pathlib import Path

# Packages outside standard library
import requests
import matplotlib.pyplot as plt
import pytz

# the two lines below are used to avoid pandas / matplotlib complaining
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


# ======================== info on how data is formatted =====================


# Keys in DarkSky data
ds_names = ['time', 'temperature', 'humidity', 'pressure',
            'windSpeed', 'windGust', 'windBearing',
            'precipIntensity', 'visibility', 'cloudCover']

# Keys in OpenWeatherMap data
ow_names = ['dt', 'temp', 'humidity', 'pressure',
            'wind_speed', 'wind_gust', 'wind_deg',
            'rain', 'visibility', 'clouds']

# Corresponding keys here
out_names = ['t', 'T', 'RH', 'P',
             'wind speed', 'wind gust', 'wind direction',
             'rain', 'visibility', 'clouds']

# keys or raw data dictionary depending on source
in_names = {'darksky': ds_names,
            'owm': ow_names}

# key for current weather conditions depending on source
current_names = {'darksky': 'currently',
                 'owm': 'current'}

# keys for time depending on source
time_names = {'darksky': 'time',
              'owm': 'dt'}

# prefixes to filenames for data saving
prefixes = {'darksky': 'DarkSky',
            'owm': 'OWM'}


# ----------------------------------------------------------------------------
# ========================== Main Weather Class ==============================
# ----------------------------------------------------------------------------


class Weather:
    """Class to manage weather data from DarkSky or OpenWeatherMap"""

    def __init__(self, location, source='darksky', api_key=None):
        """Init Weather object.

        Parameters
        ----------
        - location: tuple of (lat, long) coordinates
        - source: 'darksky' (default) or owm (OpenWeatherMap)
        - api_key: str (API key to access DarkSky or OpenWeatherMap)
        """
        self.location = location
        self.source = source
        self.api_key = api_key
        self.in_names = in_names[source]
        self.latitude, self.longitude = self.location

    # ========================== MISC Private Tools ==========================

    def _format_data(self, data, name):
        """Tool used in _format()."""
        try:
            val = data[name]
        except KeyError:
            val = None
        return val

    def _get_time(self, data):
        """Get aware datetime corresponding to data, depending on source.

        Input
        -----
        - data: dict or raw data (depends on source)

        Output
        ------
        - timezone-aware datetime corresponding to 'currently' time in data
        """
        timezone = pytz.timezone(data['timezone'])
        current_name = current_names[self.source]
        time_name = time_names[self.source]
        unix_time = data[current_name][time_name]
        return datetime.fromtimestamp(unix_time, timezone)

    def _generate_filename(self, date):
        """.json Filename (str) to store data correponding to specific date."""
        year, month, day = date.year, date.month, date.day
        prefix = prefixes[self.source]
        coord = f'{self.latitude},{self.longitude}'
        return f'{prefix}_{coord},{year:04d}-{month:02d}-{day:02d}.json'

    def _manage_chosen_days(self, date, until, ndays):
        """Return list of datetime.datetimes corresponding to user input."""
        if date is None:
            return datetime.now(),
        if until is None and ndays is None:  # just one day to download
            ndays = 1
        elif until is not None and ndays is None:  # specify start and end date
            ndays = (until - date).days + 1  # number of days to load
        elif until is None and ndays is not None:  # specify number of days
            pass
        else:
            raise ValueError('Cannot use `until` and `ndays` arguments at the same time')
        dates = [date + timedelta(days=day) for day in range(ndays)]
        return dates

    def _download(self, date, path):
        """Download single day of data (fetch + save). To be threaded."""
        data = self.fetch(date)
        self.save(data, path)

    def _download_batch(self, dates, path):
        """Threaded downloading of whole days of data."""
        if len(dates) < 1:
            return
        threads = []
        tstart = time.time()
        print(f'Download started in folder {path}')

        for date in dates:
            thread = threading.Thread(target=self._download, args=(date, path))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        print(f'Download finished in {time.time() - tstart:.2f} seconds.')

    def _hourly_data(self, data):
        """Check if there is hourly data in RAW darksky data, if yes return it."""
        try:
            if self.source == 'darksky':
                hourly_data = data['hourly']['data']
            elif self.source == 'owm':
                hourly_data = data['hourly']
        except KeyError:
            date = self._get_time(data)
            date_str = datetime.strftime(date, '%x')
            print(f'Warning: No hourly data on {date_str}.')
            return None
        else:
            return hourly_data

    def _format(self, data, timezone):
        """
        Converts raw data into usable data in weatherov (dict of names and values)
        Used by current() and hourly()
        """
        data_out = []

        for dataname in self.in_names:

            # For time, transform into timezone-aware datetime
            if dataname in time_names.values():
                unix_time = data[dataname]
                x = datetime.fromtimestamp(unix_time, timezone)

            # For any other quantity than time, manage when absent from dict
            else:
                x = self._format_data(data, dataname)

            # For humidity & clouds, put the value initially in 0-1 in 0-100%
            if dataname in ['humidity', 'cloudCover'] and x is not None \
                    and self.source == 'darksky':
                x = 100 * x

            # for OpenWeatherMap data, units come in m/s
            if dataname in ['wind_speed', 'wind_guest'] and x is not None:
                x = 3.6 * x

            # for OpenWeatherMap data, rain is a dict with keys '1h' or '3h'
            if dataname == 'rain':
                x = x['1h'] if x is not None else 0

            data_out.append(x)

        formatted_data = dict(zip(out_names, data_out))
        return formatted_data

    # ========================= Basic public methods =========================

    def url(self, date=None):
        """Generate URL (str) for request to DarkSky/OpenWeatherMap

        Parameters
        ----------
        date:
            - if None (default), current conditions.
            - if datetime.datetime object, historical data of that day.

        Output
        ------
        - URL address (str) where json data can be accessed from in a browser.
        """
        if self.source == "darksky":

            website = 'https://api.darksky.net/forecast/'
            base = f'{website}{self.api_key}/{self.latitude},{self.longitude}'
            units = 'ca'  # (ca units is SI but ensures that wind is in km/h)

            if date is None:  # current conditions
                address = f'{base}?units={units}'
            else:
                t_unix = int(datetime.timestamp(date))
                address = f'{base},{t_unix}?units={units}'

        elif self.source == "owm":

            website = 'https://api.openweathermap.org/data/2.5/onecall'
            units = 'metric'  # to have temperature in °C and not K

            if date is None:  # current conditions
                address = f'{website}?lat={self.latitude}&lon={self.longitude}' \
                          f'&appid={self.api_key}&units={units}'

            else:
                t_unix = int(datetime.timestamp(date))
                address = f'{website}/timemachine?lat={self.latitude}&units={units}' \
                          f'&lon={self.longitude}&dt={t_unix}&appid={self.api_key}'

        return address

    def fetch(self, date=None):
        """Download weather data at a specified date and return raw data.

        Typically, will return a whole day, including forecast if date is in
        the current day.

        Input
        -----
        date:
            - if None (default), current conditions.
            - if datetime.datetime object, historical data of that day.

        Output
        ------
        - dictionary of raw data corresponding to the DarkSky .json file
        """
        address = self.url(date)
        try:
            data = requests.get(address).json()
        except Exception:
            date = datetime.now() if date is None else date
            date_str = datetime.strftime(date, '%x')
            print(f'Download error for {date_str}. Please try again.')
            return None

        return data

    def save(self, data, path='.'):
        """Save raw data gotten from API call (fetch) to .json file.

        Parameters
        ----------
        - data: raw data (dict) obtained by fetch()
        - path: str or path object of folder in which to save data as .json
        (name of the file is determined automatically from data characteristics)
        """
        date = self._get_time(data)
        filename = self._generate_filename(date)

        foldername = Path(path)
        foldername.mkdir(parents=True, exist_ok=True)

        savefile = foldername / filename

        with open(savefile, 'w', encoding='utf8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load(self, date=None, path='.'):
        """Load raw data (single day) from .json file

        Parameters
        ----------
        - date is either None ('now', default), or a datetime.datetime
        - folder is a string representing a path where data files are stored

        Output
        ------
        Dictionary of raw data corresponding to the original API call (fetch).
        """
        date = datetime.now() if date is None else date
        file = Path(path) / self._generate_filename(date)

        with open(file, 'r', encoding='utf8') as f:
            data = json.load(f, )

        return data

    # ================= High-Level Public Methods (raw data )=================

    def download(self, date=None, path='.', until=None, ndays=None):
        """Download (fetch + save) weather data of one or several days.

        Input
        -----
        - date:
            - if None (default), current conditions.
            - if datetime.datetime object, historical data of that day.

        - path: str or path object of folder in which to save data as .json
        (name of the file is determined automatically from data characteristics)

        If one wants to download more than one day, one can specify
        EITHER
        - until (datetime.datetime), download data from `date` to `until` included
        OR
        - ndays (int): total number of days to download, starting at `date`
        """
        dates = self._manage_chosen_days(date, until, ndays)
        self._download_batch(dates, path)

        # Check if any missing files, and re-download them if necessary ------
        while len(self.missing_days(date, path, until=until, ndays=ndays)) > 0:
            self.download_missing_days(date, path, until=until, ndays=ndays)

    def missing_days(self, date=None, path='.', until=None, ndays=None):
        """Check for missing days in downloaded data.

        Parameters
        ----------
        see Weather.download()
        """
        dates = self._manage_chosen_days(date, until, ndays)
        missing_days = []

        for date in dates:
            file = Path(path) / self._generate_filename(date)
            if file.exists() is False:
                missing_days.append(date)

        dmin = datetime.strftime(min(dates), '%x')
        dmax = datetime.strftime(max(dates), '%x')

        if len(missing_days) == 0:
            print(f'No missing days in {path} between {dmin} and {dmax}')
        else:
            n_miss = len(missing_days)
            print(f'{n_miss} missing days found in {path} between {dmin} and {dmax}')

        return missing_days

    def download_missing_days(self, date=None, path='.', until=None, ndays=None):
        """
        Check if there are missing days between two dates and download them.

        Inputs / Outputs are the same as download()
        """
        missing_days = self.missing_days(date, path, until, ndays)
        self._download_batch(missing_days, path)

    # ============== High-level public methods (formatted data) ==============

    def current(self, date=None):
        """Return weather condition at a specific time, from the internet.

        Parameters
        ----------
        - date is either 'now' (default), or a datetime (datetime.datetime)
          that corresponds to a moment in the past

        Output
        ------
        Dictionary of raw (source-dependent) or general formatted data
        {'t': t, 'T': T, 'RH': RH ...} where T, RH etc. are single numbers
        correspond to the weather conditions at time t.
        """
        data = self.fetch(date)
        timezone = pytz.timezone(data['timezone'])

        # Convert raw data to formatted data not dependent on source
        name = current_names[self.source]
        formatted_data = self._format(data[name], timezone)

        return formatted_data

    def hourly(self, date=None, path=None, until=None, ndays=None):
        """Return hourly weather for a specific day (date in datetime format).

        Parameters
        ----------
        - date is either 'now' (default), or a datetime (datetime.datetime)
          that corresponds to a a day in the past

        - path: folder in which data is stored (if None, fetches from internet)

        If one wants to download more than one day, one can specify
        EITHER
        - until (datetime.datetime), download data from `date` to `until` included
        OR
        - ndays (int): total number of days to download, starting at `date`

        Output
        ------
        Dictionary of formatted data {'t': ts, 'T': Ts, 'RH': RH ...} where ts,
        Ts, etc. are lists (length 24) corresponding to hourly data
        """
        dates = self._manage_chosen_days(date, until, ndays)
        formatted_data = {}

        # affect empty list to every data type; will be filled with hourly data
        for outname in out_names:
            formatted_data[outname] = []

        for date in dates:

            data = self.fetch(date) if path is None else self.load(date, path)
            timezone = pytz.timezone(data['timezone'])

            hourly_data = self._hourly_data(data)

            if hourly_data is None:  # if no hourly data, go to next day
                pass
            else:
                for hdata in hourly_data:  # loops over hours of that day

                    fmt_data = self._format(hdata, timezone)

                    for outname in out_names:
                        formatted_data[outname].append(fmt_data[outname])

        return formatted_data


# ----------------------------------------------------------------------------
# ============================ Plotting Function =============================
# ----------------------------------------------------------------------------


def plot(data, title=None):
    """
    Plots hourly data of temperature, humidity and wind on a single graph.

    Input
    -----
    - formatted data (dict from weather_pt, day, or weather_days)
    - optional title of graph

    Output
    ------
    figure and axes: fig, axa, axb (axa is a tuple of main ax, axb secondary)
    """
    t = data['t']
    T = data['T']
    RH = data['RH']
    w = data['wind speed']
    wmax = data['wind gust']
    wdir = data['wind direction']
    rain = data['rain']
    clouds = data['clouds']

    T_color = '#c34a47'
    RH_color = '#c4c4cc'
    w_color = '#2d5e46'
    dir_color = '#adc3b8'
    rain_color = '#a2c0d0'
    cloud_color = '#3c5a6a'

    fig, axs = plt.subplots(1, 3, figsize=(12, 3))
    ax0a, ax1a, ax2a = axs


    # SUBPLOT 0 -- Temperature and RH ----------------------------------------

    ax0b = ax0a.twinx()  # share same x axis for T and RH

    ax0b.bar(t, RH, width=0.042, color=RH_color)
    ax0a.plot(t, T, '.-', color=T_color)

    ax0a.set_ylabel('T (°C)', color=T_color)
    ax0a.tick_params(axis='y', labelcolor=T_color)

    ax0b.set_ylabel('%RH', color=RH_color)
    ax0b.tick_params(axis='y', labelcolor=RH_color)

    ax0a.set_zorder(1)  # to put fist axis in front
    ax0a.patch.set_visible(False)  # to see second axis behind

    ax0b.set_ylim(0, 100)


    # SUBPLOT 1 -- Wind ------------------------------------------------------

    ax1b = ax1a.twinx()  # same for wind speed and wind direction

    ax1a.plot(t, w, '.-', color=w_color)
    ax1a.plot(t, wmax, '--', color=w_color)
    ax1b.bar(t, wdir, width=0.042, color=dir_color)

    ax1a.set_ylim(0, None)
    ax1a.set_ylabel('Wind speed (km/h)', color=w_color)
    ax1a.tick_params(axis='y', labelcolor=w_color)

    ax1b.set_ylabel('Wind direction', color=dir_color)
    ax1b.tick_params(axis='y', labelcolor=dir_color)

    ax1b.set_ylim(0, 360)
    ax1b.set_yticks([0, 45, 90, 135, 180, 225, 270, 315, 360])
    ax1b.set_yticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N'])

    ax1a.set_zorder(1)  # to put fist axis in front
    ax1a.patch.set_visible(False)  # to see second axis behind


    # SUBPLOT 2 -- Rain and Clouds -------------------------------------------

    ax2b = ax2a.twinx()  # same for wind speed and wind direction

    ax2b.bar(t, rain, width=0.042, color=rain_color)
    ax2a.plot(t, clouds, '.:', color=cloud_color)

    ax2a.set_ylabel('Cloud cover (%)', color=cloud_color)
    ax2a.tick_params(axis='y', labelcolor=cloud_color)

    ax2b.set_ylabel('Rain (mm/h)', color=rain_color)
    ax2b.tick_params(axis='y', labelcolor=rain_color)

    ax2a.set_ylim(0, 100)


    # finalize figure --------------------------------------------------------

    axa = (ax0a, ax1a, ax2a)
    axb = (ax0b, ax1b, ax2b)

    tmin = min(t)
    tmax = max(t)
    dt = (tmax - tmin) / 60

    for ax in axa:
        ax.set_xlim((tmin, tmax + dt))  # the +dt is for the last timestamp to appear

    if title is not None:
        fig.suptitle(title)

    fig.autofmt_xdate()
    fig.tight_layout()

    fig.show()

    return fig, axa, axb
