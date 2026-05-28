# KNMI UV Index for Home Assistant

[![Validate](https://github.com/SurfHost/ha-knmi-uv-index/actions/workflows/validate.yml/badge.svg)](https://github.com/SurfHost/ha-knmi-uv-index/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that shows the **UV index (UV radiation / "zonkracht")** forecast for the Netherlands, using the [KNMI Data Platform `uv-index` dataset](https://dataplatform.knmi.nl/dataset/access/uv-index-1-0).

KNMI publishes a national UV forecast (`zonkrachtverwachting`) for today and the next 8 days, with a value for **sunny** weather and for **cloudy** weather.

## Features

- **Live "UV index now"** sensor for your location, updated through the day and recorded, so you get an actual UV history graph
- Today's UV index and a UV index sensor for each forecast day (today + 8 days)
- The cloudy-weather UV index exposed as an attribute (`uv_cloudy`)
- The full multi-day forecast and today's hourly curve available as attributes
- Lightweight: pure-Python, no extra dependencies

## Data sources

- **KNMI Data Platform** (`uv-index`) — the official national daily UV forecast for the Netherlands (`zonkrachtverwachting`). Requires a free API key.
- **[Open-Meteo](https://open-meteo.com/)** air-quality API — the live, hourly, location-specific UV index for your Home Assistant home location. Free, **no API key**, CAMS model data. (No ground-measured UV is published as data for the Netherlands, so this model value is used for the live reading.)

## Requirements

- Home Assistant 2026.4 or newer
- A free KNMI Data Platform API key — **[request one here](https://developer.dataplatform.knmi.nl/register/)** (choose the *Open Data API*).

## Installation

### HACS (Recommended)

[![Add Repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SurfHost&repository=ha-knmi-uv-index&category=integration)

Or manually:

1. Open HACS in Home Assistant
2. Click the three dots menu and select **Custom repositories**
3. Add `https://github.com/SurfHost/ha-knmi-uv-index` with category **Integration**
4. Search for "KNMI UV Index" and install it
5. Restart Home Assistant

### Manual

1. Download the `custom_components/knmi_uv_index` folder
2. Place it in your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=knmi_uv_index)

Or manually:

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "KNMI UV Index"
3. Enter your KNMI Data Platform API key ([request one here](https://developer.dataplatform.knmi.nl/register/))

The forecast is national (the Netherlands), so no location needs to be chosen and only one instance is configured.

### Options

| Option | Default | Description |
|--------|---------|-------------|
| Update interval | 3600 | Polling interval in seconds (900-86400). The forecast is published once per day. |

## Sensors

### UV index now (`sensor.knmi_uv_index_now`)
- **State**: The live UV index for your location right now (Open-Meteo)
- Recorded by Home Assistant, so its history can be graphed directly
- **Attributes**: `clear_sky_uv_index`, `time`, `source`, and `hourly` (today + tomorrow as `{time, uv_index, uv_index_clear_sky}`)

### UV index (`sensor.knmi_uv_index`)
- **State**: Today's UV index for sunny weather (KNMI national forecast)
- **Attributes**: `uv_cloudy`, `date`, `weekday`, `issued`, `source_file`, and `forecast` (all days as `{date, weekday, uv_sunny, uv_cloudy}`)

### Forecast day sensors (one per day)
- **State**: That day's UV index for sunny weather (KNMI)
- **Name**: "Today", "Tomorrow", then the weekday + date (e.g. "Saturday 30 May")
- **Attributes**: `date`, `weekday`, `uv_cloudy`, `description`

## Graphs

Plot the live UV history with a standard History card on `sensor.knmi_uv_index_now`. For an intraday curve or the multi-day forecast, the [apexcharts-card](https://github.com/RomRider/apexcharts-card) can read the attributes, e.g. today's hourly curve:

```yaml
type: custom:apexcharts-card
header: { show: true, title: UV index today }
series:
  - entity: sensor.knmi_uv_index_now
    name: UV index
    data_generator: |
      return entity.attributes.hourly.map(p => [new Date(p.time).getTime(), p.uv_index]);
```

## Data source

UV index data is provided by the [KNMI Data Platform](https://dataplatform.knmi.nl/dataset/access/uv-index-1-0) (`uv-index`, version 1.0) — the national `zonkrachtverwachting` published by the Royal Netherlands Meteorological Institute (KNMI). An API key is required and can be requested for free at the [KNMI developer portal](https://developer.dataplatform.knmi.nl/register/).

## License

MIT
