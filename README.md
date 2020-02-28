# Weather project

## General information

Uses the Dark Sky API and database to get current weather and history. 

Requires an account at Dark Sky, which provides an API key, except when
using data that has been already downloaded from DarkSky separately

Note: the free version of the API is limited to 1000 requests per day.

In its current version, I have focused only on the following weather params:

*  temperature
*  humidity
*  wind speed (average, gusts, direction)

But more data is available if necessary (pressure, cloud cover, rain etc.).

## Summary of functions 

See `examples.py` and `help(function)` for implementation).

To produce complete RAW data (dictionary corresponding to DarkSky .json file),
use the following functions:
- `generate_url` and copy-paste the link into a browser (returns url link)
- `download_day` to get the raw data from the internet (returns dict of data)
- `load_day` to get the raw data from downloaded files (returns dict of data)

To produce FORMATTED data for analysis and plotting, use the following:
- `weather_pt`  (returns a dict of values -- data at specific time)
- `weather_day` (returns a dict of lists -- hourly data)
- `weather_days` (returns a dict of lists -- hourly data)

To download a bunch of data from the internet and save in a file:
- `download_days` (saves RAW data in .json format in a folder, it is a threaded
version of download_day)
- `download_missing_days` (to run after download_days if some days have failed)

To plot the data:
- `weather_plot`, with formatted data from `weather_day` or `weather_days`

## Examples

See `examples.py` for examples of code.

The file `locations.py` is used to store coordinates of cities / locations

## Module requirements

- requests
- matplotlib
- pandas (something about date formatting and registration with matplotlib)

## Python requirements

- Python >= 3.6 because of f-string formatting
