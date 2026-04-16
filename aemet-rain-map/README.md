# AEMET Rain Forecasting Map — Research Report

## Goal

Investigate what precipitation forecast data AEMET publishes via its Open Data API
and prototype an interactive browser map of Spain with an animated rain intensity overlay.

---

## Findings

### 1. AEMET OpenData REST API

Base URL: `https://opendata.aemet.es/opendata/api`  
Auth: free API key (email registration, 3-month validity)  
Swagger UI: https://opendata.aemet.es/dist/index.html

The API exposes these precipitation-relevant products:

| Endpoint | What it returns | Format | Update |
|---|---|---|---|
| `/red/radar/nacional` | National radar composite | PNG image | ~30 min |
| `/red/radar/regional/{id}` | Regional radar imagery | PNG image | ~30 min |
| `/red/rayos/mapa/` | Lightning strike map | PNG image | real-time |
| `/prediccion/especifica/municipio/horaria/{id}` | Hourly forecast per municipality | JSON | daily |
| `/prediccion/especifica/municipio/diaria/{id}` | Daily forecast per municipality | JSON | daily |
| `/mapasygraficos/mapassignificativos/{scope}/{day}/` | Significant weather maps | image | - |
| `/avisos_cap/ultimoelaborado/area/{area}` | CAP-format adverse weather alerts | XML/JSON | live |

**Key limitation**: Radar endpoints return static PNG images, not georeferenced tiles.
A separate "georeferenced download" endpoint exists (`/en/api-eltiempo/radar/download/compo`)
but is not straightforward to use as a browser tile layer without additional setup.

The **municipal hourly forecast** JSON includes `probPrecipitacion` (probability %) and
`precipitacion` (mm) per hour for up to 3 days, covering every Spanish municipality
(~8,000 localities). Good for point data but not a continuous spatial field.

### 2. AEMET HARMONIE-AROME Model Data

AEMET runs HARMONIE-AROME operationally at **2.5 km horizontal resolution, 65 vertical
levels**, using ECMWF HRES-IFS as boundary conditions. It is Spain's primary short-range
NWP system (successor to HIRLAM).

The model output is published on the MITECO open data catalog:
https://datos.gob.es/en/catalogo/e05068001-datos-del-modelo-harmonie-arome

| Property | Value |
|---|---|
| Spatial resolution | 0.025° (~2.5 km) |
| Temporal resolution | 1 hour |
| Forecast horizon | 48 hours |
| Variables | temperature, pressure, cloudiness, wind, **precipitation**, lightning, max wind gust |
| Format | GeoTIFF (.tif) or GeoJSON (.geojson) |
| CRS | EPSG:4326 |
| Coverage | Peninsula + Balearics (separate endpoint for Canary Islands) |
| License | CC BY 4.0 |

**Practical issue**: The MITECO catalog distribution endpoints (`catalogo.datosabiertos.miteco.gob.es`)
returned SSL certificate errors during research and the exact API call structure (parameters
for selecting variable, time step, etc.) could not be confirmed from documentation alone.
Parsing GeoTIFF in the browser also requires a library (e.g., geotiff.js).

This remains the ideal native source but requires additional engineering to consume.

### 3. Alternative Data Sources

#### Open-Meteo (`https://api.open-meteo.com`)

- **Free**, no API key, non-commercial use
- Multi-location batch API: comma-separated lat/lon in a single request
- Verified: 54-point grid over Spain returns correctly ordered array in ~400 ms
- Best-fit model auto-selection (`best_match`) or explicit model (`icon_seamless`,
  `meteofrance_arome`, `ecmwf_ifs025`)
- `precipitation` variable: mm total from preceding hour
- 72 hours at hourly resolution with `forecast_days=3`

#### RainViewer API (`https://api.rainviewer.com`)

- **Free**, no API key, global coverage
- Past 2h of radar observations at 10-minute intervals (13 frames)
- Tiles served as standard `{z}/{x}/{y}` raster tiles (max zoom 7)
- Tile URL: `{host}{path}/{size}/{z}/{x}/{y}/{colorScheme}/{options}.png`
- Frame list: `GET https://api.rainviewer.com/public/weather-maps.json`
- Verified: tiles return valid PNG, tile server is fast
- **Limitation**: observational only — no forecast

---

## Prototype: `index.html`

A single-file web application (no build step, CDN-only dependencies) implementing:

**Stack**
- MapLibre GL JS (WebGL map renderer)
- OpenStreetMap base tiles (desaturated)
- RainViewer API for past radar overlay
- Open-Meteo batch API for 48h forecast grid

**Architecture**

```
Unified timeline: past 2h (radar) ────────── now ────────── future 48h (forecast)
                  10-min frames                              hourly steps
```

- **Past frames**: RainViewer radar tiles added as a MapLibre raster source,
  one layer per frame (previous layer removed on navigation to save GPU memory)
- **Forecast frames**: 54-point grid (6 lats × 9 lons, 1.5° spacing) fetched from
  Open-Meteo in a single batch request; rendered as a MapLibre circle layer with
  `circle-color` interpolated from precipitation value (mm/h)
- **Color scale**: transparent → cyan (0.1 mm/h) → green (0.5) → yellow (2)
  → orange (5) → red (10) → purple (25+)
- **Time slider** scrubs from −2h to +48h; layer type switches automatically at
  the radar/forecast boundary
- **Play button** animates at 650 ms/frame

**To run locally:**
```bash
python3 -m http.server 8765
# open http://localhost:8765/index.html
```

**Screenshot of UI (conceptual):**
```
┌─────────────────────────────────────────────────────────────┐
│ Spain Rain Forecast  Past 2h radar + 48h forecast           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                [MapLibre map of Spain]                      │
│           [radar tiles or forecast circles overlay]         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ ▶ Play  [══════════════●════════════════]  14:30 16 Apr +2h │
│ ● 13 radar frames | 72h forecast · 54 grid pts  [Forecast]  │
│ ☑ Radar (past)  ☑ Forecast (future)   0.1 1 5 15 40mm/h   │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Decisions and Trade-offs

| Decision | Chosen | Alternative | Reason |
|---|---|---|---|
| Map library | MapLibre GL JS | Leaflet | WebGL raster layers, better tile performance |
| Forecast data | Open-Meteo batch | AEMET HARMONIE GeoTIFF | No auth, simple JSON, SSL issues with MITECO |
| Radar data | RainViewer tiles | AEMET `/red/radar/nacional` | Tile-based (not single PNG), free, no CORS issues |
| Forecast rendering | Circle layer | IDW interpolation (maplibre-gl-interpolate-heatmap) | Simpler, no build step; plugin has no UMD/CDN build |
| Grid spacing | 1.5° (~54 pts) | 0.5° (~450 pts) | Single API call; readable at zoom 5 |

---

## Open Questions and Next Steps

1. **AEMET HARMONIE native access**: Confirm the MITECO API endpoint parameters for
   selecting variable (precipitation), time step (hours 0–47), and output format (GeoJSON).
   If accessible, this could replace Open-Meteo for higher fidelity Spanish model data.

2. **Georeferenced radar**: Investigate `/en/api-eltiempo/radar/download/compo` — does it
   return GeoTIFF? What are its CORS headers? If usable, this would give native AEMET
   radar data as a proper raster overlay.

3. **IDW interpolation**: For smoother forecast rendering, the
   `maplibre-gl-interpolate-heatmap` library (GPU-based IDW via WebGL shaders) would give
   continuous raster output from the grid points. Requires a build step or UMD bundle.

4. **Météo-France AROME coverage**: Verify whether `meteofrance_arome` model on Open-Meteo
   covers all of Spain (1 km resolution, 4-day horizon) or only the northeast near the
   Pyrenees. If full coverage, it would be a better model than `best_match` for this use case.

5. **AEMET API key**: Register for a key and test rate limits and the exact JSON structure
   of the hourly municipal forecast endpoint for precipitation fields.

6. **WMS/WMTS**: AEMET likely exposes HARMONIE output via a standard OGC WMS/WMTS service
   for its internal web products. If accessible, this would give server-rendered raster tiles
   natively — the simplest possible overlay, no client-side data parsing.
