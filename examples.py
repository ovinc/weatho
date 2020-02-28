""" Examples of weather data download and plot plotting using Dark Sky data
and functions from the darksky module in the weather project (O. Vincent)

All %% cells are independent (except when specified), but need the initial 
imports, as well as an api_key for DarkSky.net (free if <1000 calls/day)
stored as a string in the variable api_key
"""

import weatherov as wov

# import GPS coordinates of some cities
from locations import Lyon, Paris, Marseille

# general imports
from datetime import datetime, timedelta


# %% 
key = api_key  # see docstring above 


# %% get single weather point at current time --------------------------------

data = wov.weather_pt(Lyon, 'now', key)
print(data)

# %%  also possible to get the url to see the raw data in json format:
url = wov.generate_url(Lyon, 'now', key)
print(url)


# %% get single weather point at specified time in history -------------------

year = 2020
month = 2
day = 7
hours = 14
minutes = 7
seconds = 10

time = datetime(year, month, day, hours, minutes, seconds)

data = wov.weather_pt(Paris, time, key)
print(data)

# also possible to get the url to see the raw data in json format:
url = wov.generate_url(Paris, time, key)
print(url)


# %% get hourly data for a given day in history, from the internet (DarkSky)

year = 2020
month = 1
day = 1

date = datetime(year, month, day)

data = wov.weather_day(Lyon, date, key)
# or
#data = wov.weather_day(Lyon, date, api_key=key, source='internet')

wov.weather_plot(data)


# %% download hourly data for a given day in history, and save data into a file

year = 2020
month = 1
day = 1

date = datetime(year, month, day)

wov.download_day(Lyon, date, key, save=True, folder='Test')

# %% load hourly data from downloaded file (needs to be run after above cell)

data = wov.weather_day(Lyon, date, source='Test')
# (no need for the key here, because it's already downloaded)
wov.weather_plot(data)


# %% get hourly data for n successive days in history, from the internet -----

year = 2020
month = 2
day = 4

n = 4

date = datetime(year, month, day)

#data = wov.weather_days(Marseille, date, n, key)
# or
data = wov.weather_days(Marseille, date, n, key, source='internet')

# plot data
wov.weather_plot(data)


# %% download hourly data for several days between date 1 and date 2, and
# save the data into files

year = 2020
month = 2
day = 4

date1 = datetime(year, month, day)
date2 = date1 + timedelta(days=4)

wov.download_days(Lyon, date1, date2, key, save=True, folder='Data/Test')
# or
# wov.download_days(Lyon, date1, date2, key, folder='Data/Test')

# download missing days if necessary
wov.download_missing_days(Lyon, date1, date2, key, save=True, folder='Data/Test')



# %% get hourly data for n successive days in history, from saved files ------
# (needs to be run after above cell)

data = wov.weather_days(Lyon, date, 5, source='Data/Test')
wov.weather_plot(data)

