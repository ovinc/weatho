""" Examples of weather data download and plot plotting using Dark Sky data
and functions from the darksky module in the weather project (O. Vincent)

All %% cells are independent (except when specified), but need the initial
imports, as well as an api_key for DarkSky.net (free if <1000 calls/day)
stored as a string in the variable api_key, and city coordinate imports
"""
# %% Imports

import weatherov as wov

# import GPS coordinates of some cities
from weatherov.locations import coordinates

# general imports
from datetime import datetime, timedelta


# %%
key = api_key  # see docstring above

# %% Define location coordinates and corresponding Weather objects
Lyon = coordinates['Lyon']
Paris = coordinates['Paris']

wlyon = wov.Weather(Lyon, api_key=key)
wparis = wov.Weather(Paris, api_key=key)

# %% get single weather point at current time --------------------------------

data = wlyon.weather_pt()
print(data)

# %%  also possible to get the url to see the raw data in json format:
url = wlyon.generate_url()
print(url)


# %% get single weather point at specified time in history -------------------

year = 2020
month = 2
day = 7
hours = 14
minutes = 7

time = datetime(year, month, day, hours, minutes)

data = wparis.weather_pt(time)
print(data)

# also possible to get the url to see the raw data in json format:
url = wparis.generate_url(time)
print(url)


# %% get hourly data for a given day in history, from the internet (DarkSky)

year = 2021
month = 1
day = 1

date = datetime(year, month, day)

data = wlyon.weather_day(date)

wov.weather_plot(data)


# %% download hourly data for a given day in history, and save data into a file

year = 2021
month = 1
day = 1

date = datetime(year, month, day)

wlyon.download_day(date, save=True, folder='Test')

# %% load hourly data from downloaded file (needs to be run after above cell)

data = wlyon.weather_day(date, source='Test')
# (no need for the key here, because it's already downloaded)
wov.weather_plot(data)


# %% get hourly data for n successive days in history, from the internet -----

year = 2021
month = 2
day = 4

n = 4

date = datetime(year, month, day)

data = wparis.weather_days(date, n)

# plot data
wov.weather_plot(data)


# %% download hourly data for several days between date 1 and date 2, and
# save the data into files

year = 2021
month = 2
day = 4

date1 = datetime(year, month, day)
date2 = date1 + timedelta(days=4)

wlyon.download_days(date1, date2, folder='Test')

# download missing days if necessary (now it's also run automatically at the
# end of download_days, once).
wlyon.download_missing_days(date1, date2, folder='Test')


# %% get hourly data for n successive days in history, from saved files ------
# (needs to be run after above cell)

data = wlyon.weather_days(date, 5, source='Test')
wov.weather_plot(data)


# %%
