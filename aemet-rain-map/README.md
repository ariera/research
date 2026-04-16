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

## Path to Sub-Kilometer Resolution

### Why 2.5 km is not the floor

Everything discussed so far — HARMONIE-AROME, Open-Meteo, RainViewer — sits at 1–2.5 km
resolution. Getting into the **100s-of-meters** range requires a different data source
entirely: **raw single-site weather radar**.

### The resolution landscape

| Source | Resolution | Type | Free? |
|---|---|---|---|
| AEMET HARMONIE-AROME | 2.5 km | NWP forecast | Yes (MITECO) |
| Météo-France AROME (Open-Meteo) | 1.3 km | NWP forecast | Yes |
| OPERA CIRRUS composite | **1 km** | Radar observation | EWC account |
| Tomorrow.io maps API | **500 m** | Radar+NWP blend | Commercial |
| AEMET single-site radar (native) | **~250–500 m** range | Radar observation | Via RODEO/OPERA |
| pySTEPS nowcast on native radar | **~250–500 m** | 0–2h extrapolation | Open source |

Sub-1 km **forecast** NWP does not exist operationally for Spain — 1.3 km (AROME) is the
hard floor. Below that, you are in Large Eddy Simulation territory, research-only.

Sub-1 km **observations** are real, via radar physics.

---

### AEMET's radar network

AEMET operates **15 C-band Doppler radars** across the Iberian Peninsula and islands.
C-band (5 GHz) radar characteristics relevant to resolution:

- **Range resolution**: 250–500 m (determined by pulse width / range bin spacing, which
  AEMET configures per site — most modern dual-pol C-band systems operate at 250 m)
- **Azimuth resolution**: 1° (fixed by the antenna rotation; translates to ~875 m
  tangential width at 50 km range, ~1,750 m at 100 km)
- **Effective resolution in practice**: best within ~80 km of a radar site; at short range
  (< 50 km) you are genuinely in the 300–600 m class for range × azimuth cells

What AEMET publishes via its OpenData API (the PNG composite) is already resampled and
degraded to a ~1 km Cartesian grid. The raw polar volume data is finer and lives elsewhere.

---

### Where the raw data lives: OPERA / RODEO

**EUMETNET OPERA** collects real-time radar volume scans from all European NMHSs,
including AEMET, in **ODIM HDF5** format. These are the native polar volumes —
each elevation angle as a PPI (Plan Position Indicator) scan, full azimuth × range
resolution.

**RODEO** (rodeo-project.eu) is an EU-funded project (running through Dec 2025) building
open APIs for all European single-site radar data under the EU High-Value Dataset
regulation. Once live:
- Access: HTTP API + bulk S3 download
- Format: ODIM HDF5
- Licence: CC BY 4.0
- Coverage: all EUMETNET members — Spain included
- 24 h rolling cache + multi-year archive

Currently, the OPERA archive is also available on the **European Weather Cloud (EWC)**
S3 buckets (accessible to registered researchers at no cost, via either the ECMWF or
EUMETSAT cloud sides).

---

### Processing pipeline: reflectivity → precipitation rate

Raw AEMET radar data gives you **reflectivity** (dBZ), not rain rate (mm/h). Converting
one to the other is a well-understood but non-trivial pipeline:

```
ODIM HDF5 (polar volume, dBZ)
    │
    ▼  [wradlib]
    1. Read & decode HDF5 — polar array (azimuths × range bins) per elevation
    2. Clutter removal  — filter static ground echoes (GABELLA or fuzzy logic method)
    3. Attenuation correction — C-band is attenuated by heavy rain; correct iteratively
       (e.g. Kraemer et al. ZPHI method built into wradlib)
    4. Z–R conversion — apply a Z–R relationship:
         Marshall-Palmer:  Z = 200 · R^1.6
         or local calibration — AEMET uses its own coefficients operationally
    5. Cartesian reprojection — reproject polar → EPSG:4326 grid at target resolution
       (e.g. 250 m cell size using wradlib's georef module)
    │
    ▼
Cartesian rain-rate grid (mm/h) at ~250 m resolution
```

**wradlib** (https://wradlib.org) is the standard Python library for all of this.
It has native ODIM HDF5 readers, GABELLA clutter filter, C-band attenuation correction,
and reprojection utilities. Actively maintained, Apache 2.0 licence.

---

### Nowcasting: extending the radar field forward in time

Once you have a sequence of Cartesian rain-rate grids (e.g. one every 5 minutes from
OPERA), **pySTEPS** (https://pysteps.github.io) extrapolates that field forward in
time at the same spatial resolution — typically producing a **0–2 hour nowcast** at
**~250–500 m**.

pySTEPS approach:
1. Compute motion field from consecutive radar frames (optical flow — Lucas-Kanade or
   cross-correlation)
2. Decompose the precipitation field into a cascade of spatial scales
3. Extrapolate each scale with the estimated motion, adding stochastic noise at small
   scales to represent uncertainty (STEPS = Stochastic Ensemble Prediction System)
4. Optionally blend with NWP (e.g. HARMONIE) at longer lead times

Output: ensemble of nowcast frames (e.g. 20 members × 24 time steps × 5 min) at the
native radar resolution. Deterministic (no ensemble) mode is also available and much
cheaper to compute.

```python
import pysteps
from pysteps import io, motion, nowcasts, verification

# Load last N radar composites (wradlib-processed, Cartesian mm/h)
rainrate_stack = ...   # shape (N, rows, cols)

# Estimate motion field
oflow_method = motion.get_method("LK")
velocity = oflow_method(rainrate_stack)

# Run STEPS nowcast
nowcast_method = nowcasts.get_method("steps")
forecast = nowcast_method(
    rainrate_stack[-3:],   # last 3 frames as seed
    velocity,
    timesteps=12,          # 12 × 5 min = 60 min ahead
    n_ens_members=20,
    noise_method="nonparametric",
)
# forecast shape: (20, 12, rows, cols)  — ensemble, time, y, x
```

The **ensemble mean** of this output is a single precipitation field per time step,
at native radar resolution (~250–500 m), valid from +5 min to +60 min.

---

### Full pipeline sketch: AEMET radar → sub-km nowcast map

```
AEMET radar (OPERA RODEO API or EWC S3)
    │  ODIM HDF5, ~5 min, polar volume
    ▼
wradlib pipeline (Python)
    │  clutter filter → attenuation → Z–R → Cartesian 250 m grid
    ▼
Store as GeoTIFF stack (last 30 min, 6 frames)
    │
    ▼
pySTEPS nowcast
    │  motion estimation → STEPS extrapolation
    │  output: 12 frames × 5 min = 60 min ahead, 250 m grid
    ▼
Serve as Cloud-Optimised GeoTIFF (COG) or raster tiles
    │  e.g. titiler (FastAPI-based tile server), or pre-rendered PNG tiles
    ▼
MapLibre raster source (same as RainViewer, but served from your own tile server)
    │  past radar + nowcast on unified time slider
    ▼
Browser map
```

This is a genuine sub-km precipitation map, entirely from open data. The main cost is
operational: running the pipeline every 5 minutes, storage for tiles, and a tile server.
Nothing proprietary.

---

### Simpler commercial shortcut

If the pipeline above is too heavy for the use case, **Tomorrow.io** offers a 500 m
weather maps API that can be dropped in as a MapLibre tile source with essentially no
plumbing — the same pattern used for RainViewer in the current prototype:

```javascript
map.addSource('tomorrow', {
  type: 'raster',
  tiles: ['https://api.tomorrow.io/v4/map/tile/{z}/{x}/{y}/precipitationIntensity/now.png?apikey=KEY'],
  tileSize: 256
});
```

Free tier: 500 API calls/day. Coverage: global including Spain. Resolution: ~500 m.
No radar processing, no pipeline, no tile server. Tradeoff: commercial dependency,
opaque provenance, no access to the underlying data.

---

## Open Questions and Next Steps

### Near-term (current prototype)

1. **AEMET HARMONIE native access**: Confirm the MITECO API endpoint parameters for
   selecting variable (precipitation), time step (hours 0–47), and output format (GeoJSON).
   If accessible, this could replace Open-Meteo for higher fidelity Spanish model data.

2. **Georeferenced radar**: Investigate `/en/api-eltiempo/radar/download/compo` — does it
   return GeoTIFF? What are its CORS headers? If usable, this would give native AEMET
   radar data as a proper raster overlay instead of RainViewer.

3. **Météo-France AROME coverage**: Verify whether `meteofrance_arome` on Open-Meteo
   covers all of Spain (1 km, 4-day horizon) or only the northeast near the Pyrenees.

4. **WMS/WMTS**: AEMET likely exposes HARMONIE output via an OGC WMS/WMTS service for
   its own web products. If accessible, server-rendered raster tiles — simplest possible
   overlay, no client-side parsing required.

### Sub-kilometer nowcasting path (next research sprint)

5. **Access OPERA single-site data for Spain**: Register with ECMWF's European Weather
   Cloud (EWC) and pull one hour of AEMET HDF5 radar files from the S3 archive. Confirm
   the range bin size (expected: 250 m or 500 m) and azimuth step (expected: 1°).
   Also check the RODEO API status at rodeo-project.eu for whether the open endpoint
   is live yet.

6. **wradlib pipeline proof-of-concept**: For a single radar site (e.g. Madrid, AEMET
   code `SER`) and one scan time, run the full pipeline:
   - Read ODIM HDF5 with `wradlib.io.read_opera_hdf5()`
   - Apply GABELLA clutter filter (`wradlib.clutter`)
   - Correct C-band attenuation (`wradlib.atten`)
   - Convert Z→R with Marshall-Palmer (`wradlib.zr`)
   - Reproject to 250 m Cartesian GeoTIFF (`wradlib.georef`)
   
   Expected output: GeoTIFF rain-rate grid, ~250 m cells, covering ~150 km radius around
   the radar. Validate visually against the AEMET composite PNG for the same time step.

7. **pySTEPS nowcast end-to-end**: Feed 6 consecutive Cartesian rain-rate grids (30 min)
   into pySTEPS, generate a 60-minute deterministic nowcast (12 × 5 min steps). Render
   the output frames as PNG tiles and serve via a local titiler instance. Plug the tile
   URL into the existing `index.html` prototype as a third layer (past radar / nowcast /
   NWP forecast) on the unified time slider.

8. **Multi-site composite**: Spain has 15 radars. Mosaicking them into a single national
   Cartesian grid requires merging overlapping coverage zones (distance-weighted or
   quality-weighted). wradlib has compositing utilities. This is what AEMET does
   internally to produce its national composite.

9. **Tomorrow.io quick test**: As a calibration check, add a Tomorrow.io 500 m tile
   layer alongside the OPERA-derived layer and compare visually. This gives a sense of
   how much resolution and latency the commercial product buys compared to the open
   pipeline.
