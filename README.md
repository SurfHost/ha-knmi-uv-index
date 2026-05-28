# KNMI UV Index for Home Assistant

[![Validate](https://github.com/SurfHost/ha-knmi-uv-index/actions/workflows/validate.yml/badge.svg)](https://github.com/SurfHost/ha-knmi-uv-index/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that shows the **UV index (UV radiation)** for a location in the Netherlands, using the [KNMI Data Platform `uv-index` dataset](https://dataplatform.knmi.nl/dataset/access/uv-index-1-0).

## Features

- Current UV index for a chosen location
- Maximum UV index per forecast day (today, tomorrow, and the following days)
- Location picked from your existing Home Assistant zones during setup (defaults to Home)
- Configurable update interval
- Clear-sky UV index exposed as an attribute (when available in the data)

## Requirements

- Home Assistant 2026.4 or newer, on a **64-bit** system (HAOS/Container on x86-64 or a 64-bit Raspberry Pi). The UV data is in NetCDF format and depends on the `netCDF4` library, which has no wheels for 32-bit armv7.
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
4. Choose a location from the dropdown (your Home Assistant zones, default is **Home**)

### Options

| Option | Default | Description |
|--------|---------|-------------|
| Location | Home | The zone whose coordinates are used to read the UV index |
| Update interval | 900 | Polling interval in seconds (300-21600) |

You can add the integration multiple times to track several locations.

## Sensors

### UV Index
- **State**: Current UV index at the chosen location (0 at night)
- **Attributes**: `forecast_time`, `clear_sky_uv_index`, `grid_latitude`, `grid_longitude`, `source_file`, `attribution`

### UV Index Max (per forecast day)
- **State**: Maximum UV index for that day
- **Name**: "UV Index Max Today", "UV Index Max Tomorrow", "UV Index Max +2d", …
- **Attributes**: `date`, `attribution`

## Data source

UV index data is provided by the [KNMI Data Platform](https://dataplatform.knmi.nl/dataset/access/uv-index-1-0) (`uv-index`, version 1.0). The data is published by the Royal Netherlands Meteorological Institute (KNMI). An API key is required and can be requested for free at the [KNMI developer portal](https://developer.dataplatform.knmi.nl/register/).

## License

MIT
