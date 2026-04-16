# AEMET Rain Forecasting Map — Research Notes

**Goal:** Prototype an interactive map of Spain with a rain intensity overlay driven
by AEMET Open Data. Key questions: what products exist, what formats, what resolution,
and how to render them in a browser map.

---

## Session log

### 2026-04-16 — Research findings

---

## AEMET OpenData REST API

Base URL: `https://opendata.aemet.es/opendata/api`
Auth: API key (free, request via email at opendata.aemet.es, 3-month validity)
Swagger UI: https://opendata.aemet.es/dist/index.html

### Key endpoints

**Radar / observational**
- `/red/radar/nacional` → national radar composite image (PNG, updated ~30 min)
- `/red/radar/regional/{id}` → regional radar images
- `/red/rayos/mapa/` → lightning strike map image
- `/en/api-eltiempo/radar/download/compo` → georeferenced radar data download (GeoTIFF, unconfirmed)

**Municipal forecasts (JSON)**
- `/prediccion/especifica/municipio/horaria/{municipio}` → hourly, 3-day horizon
  - Fields: `probPrecipitacion` (%), `precipitacion` (mm)
- `/prediccion/especifica/municipio/diaria/{municipio}` → daily, 6-day horizon

**Maps / graphics (images)**
- `/mapasygraficos/mapassignificativos/{ambito}/{dia}/` → significant weather maps
- `/mapasygraficos/analisis/` → analysis maps

**Alerts**
- `/avisos_cap/ultimoelaborado/area/{area}` → CAP-format warnings

### AEMET radar image format
- Returns PNG image (not tile-based)
- Updated every ~30 minutes
- Georeferenced download option exists separately
- Not trivially usable as a Leaflet/MapLibre tile layer without additional georeferencing

---

## AEMET HARMONIE-AROME model data (datos.gob.es)

Dataset: https://datos.gob.es/en/catalogo/e05068001-datos-del-modelo-harmonie-arome

- **Format**: GeoTIFF (.tif) or GeoJSON (.geojson) via API
- **CRS**: EPSG:4326 (WGS84)
- **Spatial resolution**: 0.025° (~2.5 km) for most variables including precipitation
- **Temporal resolution**: 1 hour
- **Forecast horizon**: 48 hours (from latest model run)
- **Variables**: temperature, pressure, cloudiness, wind, precipitation, lightning, max wind gust
- **Coverage**: Peninsula + Balearic Islands; Canary Islands (separate endpoints)
- **License**: CC BY 4.0

Distribution endpoints (via MITECO catalog — SSL issues observed during research):
- Peninsula/Baleares: https://catalogo.datosabiertos.miteco.gob.es/catalogo/dataset/46e25cfb-d421-425e-8077-1cd7063793a9/resource/9ba745ed-6d3f-4812-9784-11ebafad3dea
- Canarias: https://catalogo.datosabiertos.miteco.gob.es/catalogo/dataset/46e25cfb-d421-425e-8077-1cd7063793a9/resource/97f920c9-8ee5-4791-ae98-101837a724bb

**Issue**: Actual API call structure not yet confirmed; MITECO catalog returns SSL errors.

---

## HARMONIE-AROME model background

- Part of the ALADIN-HIRLAM NWP system (consortium of 26 European countries)
- Non-hydrostatic limited-area model
- AEMET runs it operationally over Spain at 2.5 km horizontal resolution, 65 vertical levels
- Boundary conditions from ECMWF HRES-IFS
- Short-range (0–48h); HIRLAM was the predecessor
- Published at climalert-docs.imida.es (regional climate alert project)

---

## Alternative data sources

### Open-Meteo (https://api.open-meteo.com)
- Free, no API key, non-commercial use
- Models available for Spain:
  - `best_match` (auto-selects best model per location)
  - `meteofrance_arome` (1 km, 4-day — covers France and neighbors, may not reach southern Spain)
  - `icon_seamless` / `icon_d2` (DWD, 2 km, ~2.5-day, Central Europe)
  - `ecmwf_ifs025` (25 km, 15-day, global)
- Batch multi-location: `?latitude=36,37.5,39&longitude=-3,-3,-3&hourly=precipitation`
- Response for multiple locations: JSON array, one object per location
- Precipitation variables: `precipitation` (mm/h total), `rain`, `showers`, `precipitation_probability`

### RainViewer API (https://api.rainviewer.com)
- Free, no API key
- Past 2h radar, 10-min intervals; infrared satellite
- Tile URL: `{host}{path}/{tileSize}/{z}/{x}/{y}/{colorScheme}/{options}.png`
  - colorScheme 2 = standard; options "1_1" = smoothed + snow detection
  - Max zoom level: 7
- Frame list: `GET https://api.rainviewer.com/public/weather-maps.json`
  → `{ host, radar: { past: [{time, path}, ...] } }`
- Works as TileLayer in Leaflet or MapLibre (raster source)
- Only observational (past/current), no forecast

---

## Prototype design

**Chosen approach:**

1. **Map library**: MapLibre GL JS from CDN (WebGL, no build step)
2. **Base tiles**: OpenStreetMap (free, desaturated)
3. **Past precipitation** (−2h to now): RainViewer radar tiles, animated
4. **Forecast precipitation** (now to +48h): Open-Meteo batch over 54-point Spain grid
   - Grid: lats [36, 37.5, 39, 40.5, 42, 43.5] × lons [-9, -7.5, -6, -4.5, -3, -1.5, 0, 1.5, 3]
   - Render as GeoJSON circle layer, color-coded by mm/h
   - Color: transparent → cyan (0.1) → green (1) → yellow (5) → orange (10) → red (25) → purple (50)
5. **Unified time slider**: −2h to +48h; auto-switches between radar and forecast layer
6. Single HTML file, no build system

**Alternative deferred**: AEMET HARMONIE-AROME GeoTIFF from datos.gob.es
- SSL cert issues; GeoTIFF parsing needs geotiff.js; Open-Meteo is simpler

---

## Open questions

- What exactly does the AEMET HARMONIE API endpoint look like (parameters, response format)?
- Does `/en/api-eltiempo/radar/download/compo` return GeoTIFF? What CORS headers does it have?
- Does `meteofrance_arome` on Open-Meteo cover all of Spain, or just near the Pyrenees?
- Is there a WMS or WMTS endpoint for AEMET HARMONIE precipitation?
