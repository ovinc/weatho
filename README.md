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

## Examples

See `examples.py` for examples of code.

The file `locations.py` is used to store coordinates of cities / locations

## Module requirements

- requests
- matplotlib
- pandas (something about date formatting and registration with matplotlib)

## Python requirements

- Python >= 3.6 because of f-string formatting
