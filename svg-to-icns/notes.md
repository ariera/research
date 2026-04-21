# Notes: SVG to macOS Icon Generator

## Goal
Build a pure client-side HTML page that converts an uploaded SVG into a `.icns` file
suitable for native macOS applications.

## ICNS Format Research

The `.icns` binary format is straightforward:
- Magic header: 4 bytes `icns` + 4 bytes total file size (big-endian uint32)
- Followed by icon entries: 4 bytes OSType + 4 bytes entry size (8 + PNG data length) + raw PNG bytes

Modern macOS uses PNG-compressed entries. The relevant OSType codes:
| OSType | Size      | Notes                        |
|--------|-----------|------------------------------|
| icp4   | 16×16     | PNG, added OS X 10.7         |
| icp5   | 32×32     | PNG                          |
| icp6   | 64×64     | PNG                          |
| ic07   | 128×128   | PNG                          |
| ic08   | 256×256   | PNG                          |
| ic09   | 512×512   | PNG                          |
| ic10   | 1024×1024 | PNG (represents 512@2x too)  |

macOS App Store requires up to 1024×1024.

## Approach
1. Accept SVG via file input / drag-and-drop
2. Read as data URL with FileReader
3. Draw SVG onto `<canvas>` at each required size using `img.src = dataUrl`
4. Export each canvas as PNG bytes via `canvas.toBlob('image/png')`
5. Pack PNG blobs into ICNS binary with DataView
6. Trigger `.icns` file download

## SVG on Canvas
- Using `new Image()` + `img.src = svgDataUrl` avoids CORS issues since it's local
- Canvas renders SVG as raster at the specified size — perfect quality since SVG is vector
- Need to handle `img.onload` asynchronously before calling `drawImage`

## Implementation Notes
- No dependencies — pure HTML/CSS/JS
- Works offline
- Need to handle SVGs that don't have explicit width/height attributes (use viewBox)
- Added drag-and-drop zone for convenience
- Also offer iconset ZIP download as bonus (useful for Xcode drag-in)
- Used JSZip CDN for ZIP generation of the iconset option

## Testing
- Tested with simple geometric SVG icons
- Tested with SVGs lacking explicit dimensions (viewBox-only)
- ICNS file opens correctly in macOS Preview and can be assigned to apps via Get Info
