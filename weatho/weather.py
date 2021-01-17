""" Download, analyze and plot weather data DarkSky or OpenWeatherMap API"""


# TODO: move from threading to concurrent futures?


# Standard Library
from datetime import datetime, timedelta
import time
import json
from pathlib import Path
from concurrent import futures

# Packages outside standard library
import requests
import pytz

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

    def _get_current_time_of_raw_data(self, data):
        """Get aware datetime corresponding to data, depending on source.

        Input
        -----
        - data: dict or raw data (depends on source)

        Output
        ------
        timezone-aware datetime corresponding to 'currently' time in data,
        using the timezone specified in the data.
        """
        try:
            timezone = pytz.timezone(data['timezone'])
        except KeyError:
            raise KeyError('No timezone information in data, '
                           'probably because of download/API error')
        else:
            current_name = current_names[self.source]  # e.g. "currently"
            time_name = time_names[self.source]        # e.g. "time"
            unix_time = data[current_name][time_name]
            return datetime.fromtimestamp(unix_time, timezone)

    def _format_date_for_filenames(self, date):
        """Format date to get correct date info for filename to load/save data

        This is because Darksky and OpenWeahterMap do not get hourly data the
        same way (see e.g. _generate_filename())

        As a result, depending on source and input date, the following happens:

        - if `date` is timezone **naive**, it is supposed that the user means
          that the corresponding datetime is expressed in:
            - local time (of location of weather data) for DarkSky,
            - UTC time for OpenWeatherMap.

        - if `date` is timezone **aware**, it will be:
            - untouched for DarkSky (assumed to be already OK --> use should be
              careful to localize the date with the correct timezone),
            - converted to UTC for OpenWeatherMap.
        """
        if date.tzinfo is not None and self.source == 'owm':
            return date.astimezone(pytz.utc)
        else:
            return date

    def _generate_filename(self, date):
        """.json Filename (str) to save/load hourly data at specific date.

        Note
        ----
        Takes into account the fact that
        - DarkSky generates hourly data from 0:00 to 23:59 in *local* time
        - OpenWeatherMap from 0:00 to 23:59 in *UTC* time
        """
        d = self._format_date_for_filenames(date)
        year, month, day = d.year, d.month, d.day
        prefix = prefixes[self.source]
        coord = f'{self.latitude},{self.longitude}'
        return f'{prefix}_{coord},{year:04d}-{month:02d}-{day:02d}.json'

    @staticmethod
    def _manage_chosen_days(date, until, ndays):
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
        try:
            self.save(data, path)
        except KeyError:
            date_str = datetime.strftime(date, '%x')
            print(f'Error for data on {date_str} (e.g. time/timezone missing due '
                  'to API error). Data not saved for this date.')
            return

    def _download_batch(self, dates, path):
        """Threaded downloading of whole days of data."""
        if len(dates) < 1:
            return
        tstart = time.time()
        print(f'Download started in folder {path}')

        with futures.ThreadPoolExecutor(max_workers=60) as executor:
            for date in dates:
                executor.submit(self._download, date, path)

        print(f'Download finished in {time.time() - tstart:.2f} seconds.')

    def _hourly_data(self, data):
        """Check if there is hourly data in RAW darksky data, if yes return it."""
        try:
            if self.source == 'darksky':
                hourly_data = data['hourly']['data']
            elif self.source == 'owm':
                hourly_data = data['hourly']
        except KeyError:
            date = self._get_current_time_of_raw_data(data)  # just for printing purposes
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
                t_unix = int(date.timestamp())
                address = f'{base},{t_unix}?units={units}'

        elif self.source == "owm":

            website = 'https://api.openweathermap.org/data/2.5/onecall'
            units = 'metric'  # to have temperature in °C and not K

            if date is None:  # current conditions
                address = f'{website}?lat={self.latitude}&lon={self.longitude}' \
                          f'&appid={self.api_key}&units={units}'

            else:
                t_unix = int(date.timestamp())
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
        - dictionary of source-specific, raw data corresponding to the API
          call (from Darksky or OpenWeatherMap)

        - Note: there is an important difference between DarkSky and OpenWeatherMap
          concerning the "hourly" data returned with the API call. Both are 24
          hours long, but :
            - DarkSky starts at 0:00 in *local* time,
            - OWM starts at 0:00 in *UTC* time
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
        date = self._get_current_time_of_raw_data(data)
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

    def download(self, date=None, path='.', until=None, ndays=None, ntries=5):
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

        - ntries is the number of times the program will check for missing data
          and try to download it again.
        """
        dates = self._manage_chosen_days(date, until, ndays)
        self._download_batch(dates, path)

        # Check if any missing files, and re-download them if necessary ------
        for _ in range(ntries):
            missing_days = self.missing_days(date, path, until=until,
                                             ndays=ndays, verbose=False)
            if len(missing_days) == 0:
                break
            else:
                self.download_missing_days(date, path, until=until,
                                           ndays=ndays)
        else:
            print(f'Warning: could not download missing data after {ntries} tries.')

    def missing_days(self, date=None, path='.', until=None, ndays=None, verbose=True):
        """Check for missing days in downloaded data.

        Parameters
        ----------
        see Weather.download(). Additional parameter:
        - verbose: if False, do not print missing day information
        """
        dates = self._manage_chosen_days(date, until, ndays)
        missing_days = []

        for date in dates:
            file = Path(path) / self._generate_filename(date)
            if file.exists() is False:
                missing_days.append(date)

        if verbose:

            mindate = self._format_date_for_filenames(min(dates))
            maxdate = self._format_date_for_filenames(max(dates))

            dmin = datetime.strftime(mindate, '%x')
            dmax = datetime.strftime(maxdate, '%x')

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
