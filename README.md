# KNMI UV Index for Home Assistant

[![Validate](https://github.com/SurfHost/ha-knmi-uv-index/actions/workflows/validate.yml/badge.svg)](https://github.com/SurfHost/ha-knmi-uv-index/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that shows the **UV index (UV radiation / "zonkracht")** forecast for the Netherlands, using the [KNMI Data Platform `uv-index` dataset](https://dataplatform.knmi.nl/dataset/access/uv-index-1-0).

KNMI publishes a national UV forecast (`zonkrachtverwachting`) for today and the next 8 days, with a value for **sunny** weather and for **cloudy** weather.

## Features

- Current UV index sensor (today's value for sunny weather)
- A UV index sensor for each forecast day (today + 8 days)
- The cloudy-weather UV index exposed as an attribute (`uv_cloudy`)
- The full multi-day forecast available as an attribute on the main sensor
- Lightweight: pure-Python, no extra dependencies

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

### UV index
- **State**: Today's UV index for sunny weather
- **Attributes**: `uv_cloudy` (today's cloudy value), `date`, `issued`, `source_file`, and `forecast` (the full list of `{date, uv_sunny, uv_cloudy}` for all days)

### UV index — Today / Tomorrow / +N days (one per forecast day)
- **State**: That day's UV index for sunny weather
- **Attributes**: `date`, `uv_cloudy`, `description`

## Data source

UV index data is provided by the [KNMI Data Platform](https://dataplatform.knmi.nl/dataset/access/uv-index-1-0) (`uv-index`, version 1.0) — the national `zonkrachtverwachting` published by the Royal Netherlands Meteorological Institute (KNMI). An API key is required and can be requested for free at the [KNMI developer portal](https://developer.dataplatform.knmi.nl/register/).

## License

MIT
