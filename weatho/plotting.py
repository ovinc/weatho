""" Download, analyze and plot weather data DarkSky or OpenWeatherMap API"""


import matplotlib.pyplot as plt


# ----------------------------------------------------------------------------
# ============================ Plotting Function =============================
# ----------------------------------------------------------------------------


def plot(data, title=None):
    """Plot hourly data of temperature, humidity and wind on a single graph.

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

    plt.show()

    return fig, axa, axb
