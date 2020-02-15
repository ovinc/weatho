""" Download, analyze and plot weather data using data from DarkSky API

See documentation of API here: https://darksky.net/dev/docs

Requires an account at Dark Sky, which provides an API key.
Note: the free version is limited to 1000 requests per day.

In its current version, I have focused only on the following weather params:
    - temperature
    - humidity
    - wind (average, gusts, direction)

But more data is available if necessary (pressure, cloud cover, rain etc.),
see e.g. the dictionary returned by functions like load_day

Olivier Vincent, 2020-02-09

"""

# TODO -- load and save data for a specific period or a whole year
# TODO -- error management, often wind Bearing is missing, just put none
# TODO -- add pressure
# TODO -- move from threading to concurrent futures
# TODO -- error or warning if someone tries to create a folder called 'internet'


import requests
from datetime import datetime, timedelta

import threading
import time
import json
from pathlib import Path

import matplotlib.pyplot as plt
# the two lines below are used to avoid pandas / matplotlib complaining
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


# ================================ functions =================================


def generate_url(location, date='now', api_key=''):
    """ formats request to DarkSky, date is 'now' or a date (datetime format)
        returns url of data, can be accessed directly in a browser (json)
    """

    (lat, lon) = location
    coord = f'{lat},{lon}'

    website = 'https://api.darksky.net/forecast/'

    base_url = website + api_key + '/' + coord
    units = 'ca'
    # (ca units is SI but ensures that wind is in km/h)

    if date == 'now':
        url = base_url + '?units=' + units
    else:
        t_unix = int(datetime.timestamp(date))
        url = base_url + f',{t_unix}' + '?units=' + units

    return url


def download_day(location, date='now', api_key='', save=False, folder=''):
    """ download single weather point (typically, will return a whole day,
    including forecast if date is in the current day. It saves the data in a
    json file if save is True, in the folder (current folder by default)
    There is an option to not save the data, because the function is also used
    by weather_pt() and weather_day() in a mode where it transfers the data
    to these functions for immediate usage without saving.
    """

    url = generate_url(location, date, api_key)
    data = requests.get(url).json()

    if save is True:

        if date == 'now': date = datetime.now()  # Warning -- date changed here

        (lat, lon) = location
        coord = f'{lat},{lon}'
        year = date.year
        month = date.month
        day = date.day

        filename = 'DarkSky_' + coord + f',{year:04d}-{month:02d}-{day:02d}.json'

        foldername = Path(folder)
        foldername.mkdir(parents=True, exist_ok=True)

        savefile = foldername / filename

        with open(savefile, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    return data # this is raw data that cannot be directly plotted with weather_plot


def download_days(location, date_start, date_end, api_key='', save=True, folder=''):
    """ download weather data (day-by-day) from DarkSky between selected dates.
    Uses threading on the function dowload_day().
    In the current version, the "save" boolean is unnecessary because there is
    nothing returned by the program except the output files, but I keep it
    there with default 'True' for similarity with download_day and in case it
    is needed in the future.
    """
    delta_t = date_end - date_start
    ndays = delta_t.days + 1  # number of days to load

    threads = []
    tstart = time.time()
    print(f'Loading started in folder {folder}')

    for day in range(ndays):
        date = date_start + timedelta(days=day)
        arguments = (location, date, api_key, save, folder)
        thread = threading.Thread(target=download_day, args=arguments)
        threads.append(thread)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    tend = time.time()
    total_time = tend - tstart

    print(f'Loading finished in {total_time} seconds. Youpi!')

    return


def load_day(location, date='now', folder=''):
    """ load weather data (single day) that has been downloaded in a folder
    using download_days, and returns usable data """

    if date == 'now': date = datetime.now()  # Warning -- date changed here

    (lat, lon) = location
    coord = f'{lat},{lon}'
    year = date.year
    month = date.month
    day = date.day

    filename = 'DarkSky_' + coord + f',{year:04d}-{month:02d}-{day:02d}.json'

    foldername = Path(folder)
    foldername.mkdir(parents=True, exist_ok=True)

    file = foldername / filename

    with open(file, 'r') as f:
        data = json.load(f)

    return data


def weather_pt(location, date='now', api_key=''):
    """ Loads weather condition at a specific time """

    data_all = download_day(location, date, api_key)
    data = data_all['currently']

    t, T, RH, w, wmax, wdir = data_to_pts(data)

    return {'t': t, 'T': T, 'RH': RH,
            'wind': w, 'gust': wmax, 'direction': wdir}


def weather_day(location, date, api_key='', source='internet'):
    """ Loads hourly weather for a specific day (date in datetime format)
    Two choices of source: 'internet' (DarkSky.net), or a foldername
    """
    if source == 'internet':
        data_all = download_day(location, date, api_key)
    else:
        data_all = load_day(location, date, source)

    data_hourly = data_all['hourly']['data']

    ts, Ts, RHs, ws, wmaxs, wdirs = [], [], [], [], [], []

    for data in data_hourly:  # loops over hours of that day

        t, T, RH, w, wmax, wdir = data_to_pts(data)

        ts.append(t); Ts.append(T), RHs.append(RH)
        ws.append(w); wmaxs.append(wmax); wdirs.append(wdir)

    return {'t': ts, 'T': Ts, 'RH': RHs,
            'wind': ws, 'gust': wmaxs, 'direction': wdirs}


def weather_days(location, date_start, ndays, api_key='', source='internet'):
    """ Loads hourly weather for several days (number of days is ndays)
    Two choices of source: 'internet' (DarkSky.net), or a foldername
    """

    ts, Ts, RHs, ws, wmaxs, wdirs = [], [], [], [], [], []

    for day in range(ndays):

        date = date_start + timedelta(days=day)

        data = weather_day(location, date, api_key, source)

        ts += data['t']
        Ts += data['T']
        RHs += data['RH']
        ws += data['wind']
        wmaxs += data['gust']
        wdirs += data['direction']

    return {'t': ts, 'T': Ts, 'RH': RHs,
            'wind': ws, 'gust': wmaxs, 'direction': wdirs}


def data_to_pts(data):
    """ Extracts data of interest from DarkSky data """

    data_time = data['time']
    t = datetime.fromtimestamp(data_time)

    T = data['temperature']
    RH = 100*data['humidity']
    w = data['windSpeed']
    wmax = data['windGust']
    wdir = data['windBearing']

    return t, T, RH, w, wmax, wdir


def weather_plot(data):
    """ Plots hourly data of temperature, humidity and wind on a single graph
    """
    t = data['t']
    T = data['T']
    RH = data['RH']
    w = data['wind']
    wmax = data['gust']
    wdir = data['direction']

    fig, (ax1, ax3) = plt.subplots(1, 2, figsize=(12, 4))
    ax2 = ax1.twinx()  # share same x axis for T and RH
    ax4 = ax3.twinx()  # same for wind speed and wind direction

    # Temperature and RH ------

    T_color = 'r'
    RH_color = 'b'

    ax1.plot(t, T, color=T_color)
    ax2.plot(t, RH, ':', color=RH_color)

    ax1.set_ylabel('T (°C)', color=T_color)
    ax1.tick_params(axis='y', labelcolor=T_color)

    ax2.set_ylabel('%RH', color=RH_color)
    ax2.tick_params(axis='y', labelcolor=RH_color)

    ax2.set_ylim(0, 100)

    # Wind ----------------------

    w_color = 'k'
    dir_color = 'g'

    ax3.plot(t, w, color=w_color)
    ax3.plot(t, wmax, '--', color=w_color)
    ax4.plot(t, wdir, '.', color=dir_color)

    ax3.set_ylabel('wind speed (km/h)', color=w_color)
    ax3.tick_params(axis='y', labelcolor=w_color)

    ax4.set_ylabel('wind direction (°)', color=dir_color)
    ax4.tick_params(axis='y', labelcolor=dir_color)

    ax4.set_ylim(0, 360)
    ax4.set_yticks([0, 45, 90, 135, 180, 225, 270, 315, 360])
    ax4.set_yticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N'])

    # finalize figure -----------

    fig.autofmt_xdate()
    fig.tight_layout()

    fig.show()
