""" Download, analyze and plot weather data DarkSky or OpenWeatherMap API"""

# TODO: move from threading to concurrent futures?
# TODO: timezone management

from datetime import datetime, timedelta
import threading
import time
import json
from pathlib import Path

import requests
import matplotlib.pyplot as plt

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


# ================================ functions =================================


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

        self.latitude, self.longitude = self.location

        self.in_names = ds_names if self.source == 'darksky' else ow_names

    def generate_url(self, date=None):
        """
        Formats URL for request to DarkSky

        Parameters
        ----------
        - date: if None (default), means now. if not, input datetime.datetime.

        Output
        ------
        - url (str) where json data can be accessed from in a browser.
        """
        if self.source == "darksky":

            website = 'https://api.darksky.net/forecast/'
            base = f'{website}{self.api_key}/{self.latitude},{self.longitude}'
            units = 'ca'  # (ca units is SI but ensures that wind is in km/h)

            if date is None:  # current conditions
                url = f'{base}?units={units}'
            else:
                t_unix = int(datetime.timestamp(date))
                url = f'{base},{t_unix}?units={units}'

        elif self.source == "owm":

            website = 'https://api.openweathermap.org/data/2.5/onecall'
            units = 'metric'  # to have temperature in °C and not K

            if date is None:  # current conditions
                url = f'{website}?lat={self.latitude}&lon={self.longitude}' \
                      f'&appid={self.api_key}&units={units}'

            else:
                t_unix = int(datetime.timestamp(date))
                url = f'{website}/timemachine?lat={self.latitude}&units={units}' \
                      f'&lon={self.longitude}&dt={t_unix}&appid={self.api_key}'

        return url

    def generate_filename(self, date):
        """Filename (str) correponding to specific date."""
        year = date.year
        month = date.month
        day = date.day
        name = 'DarkSky' if self.source == 'darksky' else 'OWM'
        coord = f'{self.latitude},{self.longitude}'
        filename = f'{name}_{coord},{year:04d}-{month:02d}-{day:02d}.json'
        return filename

    def download_day(self, date=None, save=False, folder=''):
        """
        Downloads single weather point (typically, will return a whole day,
        including forecast if date is in the current day). It saves the data in a
        json file if save is True, in the folder (current folder by default)

        There is an option to not save the data, because the function is also used
        by weather_pt() and weather_day() in a mode where it transfers the data
        to these functions for immediate usage without saving.

        Input
        -----
        - date is either None (now, default), or a datetime.datetime
        - save is boolean: save data into .json file
        - folder is a string representing a path for saving

        Output
        ------
        - dictionary of raw data corresponding to the DarkSky .json file
        """
        url = self.generate_url(date)

        date_str = date if date is None else datetime.strftime(date, '%x')

        try:
            data = requests.get(url).json()
        except Exception:
            print(f'Download error for {date_str}. Please try again.')
            return None

        if self.get_hourly_data(data) is None:
            print(f'Warning: No Hourly Data on {date_str}.')

        if save is True:

            date = datetime.now() if date is None else date
            filename = self.generate_filename(date)

            foldername = Path(folder)
            foldername.mkdir(parents=True, exist_ok=True)

            savefile = foldername / filename

            with open(savefile, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        return data

    def _download_days(self, dates, folder):
        """Threaded downloading of whole days of data."""
        threads = []
        tstart = time.time()
        print(f'Loading started in folder {folder}')

        for date in dates:
            thread = threading.Thread(target=self.download_day,
                                      args=(date, True, folder))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        tend = time.time()
        total_time = tend - tstart

        print(f'Loading finished in {total_time} seconds.')


    def download_days(self, date_start, date_end, folder='.'):
        """
        Downloads weather data (day-by-day) from DarkSky between selected dates.
        Uses threading on the function dowload_day().

        Input
        -----
        Same as download_day except that dates have to be datetimes (not 'now')
        and there is no `save` option (data is always saved in a file here).

        Ouput
        -----
        None
        """
        delta_t = date_end - date_start
        ndays = delta_t.days + 1  # number of days to load
        dates = [date_start + timedelta(days=day) for day in range(ndays)]

        self._download_days(dates, folder)

        while len(self.check_missing_days(date_start, date_end, folder)) > 0:
            self.download_missing_days(date_start, date_end, folder)

    def check_missing_days(self, date_start, date_end, folder='.'):
        """Check for missing days between two dates in downloaded data."""

        delta_t = date_end - date_start
        ndays = delta_t.days + 1  # number of days to load

        missing_days = []

        for day in range(ndays):

            date = date_start + timedelta(days=day)
            file = Path(folder) / self.generate_filename(date)

            if file.exists() is False:
                missing_days.append(date)

        if len(missing_days) == 0:
            print('No missing days found.')
        else:
            n_miss = len(missing_days)
            print(f'{n_miss} missing days found.')

        return missing_days

    def get_hourly_data(self, data):
        """Check if there is hourly data in RAW darksky data, if yes return it."""
        try:
            if self.source == 'darksky':
                data_hourly = data['hourly']['data']
            elif self.source == 'owm':
                data_hourly = data['hourly']
        except KeyError:
            return None
        else:
            return data_hourly

    def download_missing_days(self, date_start, date_end, folder='.'):
        """
        Check if there are missing days between two dates and download them.

        Inputs / Outputs are the same as download_days()
        """
        missing_days = self.check_missing_days(date_start, date_end, folder)
        if len(missing_days) < 1:
            print(f'No missing days in {folder} between {date_start} and {date_end}')
        else:
            self._download_days(missing_days, folder)

    def load_day(self, date=None, folder=''):
        """
        Loads weather data (single whole day) that has been downloaded in a folder
        using download_day or download_days.

        Parameters
        ----------
        - date is either None ('now', default), or a datetime.datetime
        - folder is a string representing a path where data is loaded from

        Output
        ------
        Dictionary of raw data corresponding to the DarkSky .json file
        """
        date = datetime.now() if date is None else date
        file = Path(folder) / self.generate_filename(date)

        with open(file, 'r') as f:
            data = json.load(f)

        return data

    def weather_pt(self, date=None):
        """
        Loads weather condition at a specific time, from the internet (DarkSky)

        Parameters
        ----------
        - date is either 'now' (default), or a datetime (datetime.datetime)

        Output
        ------
        Dictionary of formatted data {'t': t, 'T': T, 'RH': RH ...} where T, RH
        etc. are single numbers correspond to the weather conditions at time t.
        """
        data_all = self.download_day(date)
        name = 'currently' if self.source == 'darksky' else 'current'
        data = data_all[name]
        data_pts = self._data_to_pts(data)
        return data_pts

    def weather_day(self, date=None, source=None):
        """
        Loads hourly weather for a specific day (date in datetime format).

        Parameters
        ----------
        - date is either None (default, i.e. now), or a datetime.datetime
        - source is either None (requests data from internet) or a folder

        Output
        ------
        Dictionary of formatted data {'t': ts, 'T': Ts, 'RH': RH ...} where ts,
        Ts, etc. are lists (length 24) corresponding to hourly data
        """
        if source is None:
            data_all = self.download_day(date)
        else:
            data_all = self.load_day(date, source)

        data_hourly = self.get_hourly_data(data_all)

        if data_hourly is None:
            date_str = datetime.strftime(date, '%x')
            print(f'Warning: No hourly data on {date_str}. Returning None.')
            return None

        data_out = {}
        for outname in out_names:  # affect empty list to every data type
            data_out[outname] = []

        for data in data_hourly:  # loops over hours of that day

            data_pts = self._data_to_pts(data)

            for outname in out_names:
                data_out[outname].append(data_pts[outname])

        return data_out

    def weather_days(self, date_start, ndays, source=None):
        """
        Loads hourly weather for several days (number of days is ndays)

        Parameters
        ----------
        - date_start is a datetime (datetime.datetime)
        - ndays is an int (number of days)
        - source is either None (requests data from internet) or a folder

        Output
        ------
        Dictionary of formatted data {'t': ts, 'T': Ts, 'RH': RH ...} where ts,
        Ts, etc. are lists (length ndays*24) corresponding to hourly data
        """
        data_out = {}
        for outname in out_names:  # affect empty list to every data type
            data_out[outname] = []

        for day in range(ndays):

            date = date_start + timedelta(days=day)
            data = self.weather_day(date, source)

            if data is None:
                pass
            else:
                for outname in out_names:
                    data_out[outname] += data[outname]

        return data_out

    def _data_to_pts(self, data):
        """
        Converts raw data into usable data in weatherov (dict of names and values)
        Used by weather_day and weather_pt
        """
        def _formatdata(name):
            try:
                val = data[name]
            except KeyError:
                val = None
            return val

        data_out = []

        for dataname in self.in_names:

            if dataname in ['time', 'dt']:
                x = datetime.fromtimestamp(data[dataname])
            else:
                x = _formatdata(dataname)

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

        return dict(zip(out_names, data_out))


def weather_plot(data, title=None):
    """
    Plots hourly data of temperature, humidity and wind on a single graph.

    INPUT
    - formatted data (dict from weather_pt, weather_day, or weather_days)
    - optional title of graph

    OUTPUT
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
