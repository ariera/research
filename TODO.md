# Research — Improvement Ideas

---

## 1. Plugin system

**The idea:** Allow extending the app's functionality through a plugin architecture
rather than modifying core code directly.

**Things to figure out:**
- Plugin discovery and loading mechanism (entry points, directory scan, config-based)
- Hook/event system — what lifecycle events can plugins tap into
- Plugin API surface — what do plugins have access to
- Configuration: per-plugin settings
- Isolation and error handling — a broken plugin shouldn't crash the host

---

## 2. Receive via email (email-to-post)

**The idea:** Publish a blog post by sending an email to a dedicated address. The
email subject becomes the title, the body becomes the content.

**Things to figure out:**
- Inbound email handling: dedicated mailbox polling (IMAP), or an inbound email
  service (Mailgun, SendGrid, Postmark all offer inbound routing via webhooks)
- Authentication: how to verify the sender is authorized (allowlist of from-addresses,
  secret token in subject, DKIM verification)
- Content parsing: HTML email → clean post content (strip signatures, quoted replies,
  email client boilerplate)
- Attachments: handle inline images
- Workflow: publish immediately, or save as draft for review?

---

## 3. AEMET rain forecasting map

**The idea:** Prototype an interactive map of Spain with an overlaid rain intensity
layer driven by AEMET (Spanish Meteorological Agency) open data.

**Things to figure out:**

*Data research:*
- What forecast products does AEMET publish via its Open Data API (api.aemet.es)
- Data format (GRIB2, JSON, NetCDF?) and how to parse/render precipitation fields
- Spatial granularity: grid resolution, coverage (Peninsula + islands)
- Temporal granularity and update frequency per product
- Available forecast horizons — short-term (<12 h), medium (1–3 days), extended (4–7 days)

*Forecast models to investigate:*
- HIRLAM / HARMONIE-AROME (high-res short-range, ~1–2 km, hourly)
- ECMWF deterministic and ensemble (medium-range, coarser grid)
- Any AEMET-specific post-processed guidance products

*Map prototype:*
- Tile-based map (Leaflet or MapLibre GL) supporting free zoom/pan over Spain
- Precipitation overlay rendered as translucent cloud-like sprites or a smooth
  raster layer, color-coded by intensity (e.g. green → yellow → red → purple)
- Time-slider or animation to step through forecast hours
- Toggle between available models / forecast horizons
- Possible data sources if AEMET coverage is incomplete: Open-Meteo, Meteomatics,
  or self-served GRIB tiles
