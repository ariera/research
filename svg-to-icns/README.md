# SVG → macOS Icon Generator

A single-file, offline-capable HTML tool that converts an SVG into a `.icns` file
ready for native macOS applications.

## Usage

Open `index.html` in any modern browser. No server or build step required.

1. Drop an SVG file onto the page (or click to browse).
2. Preview the icon rendered at all standard macOS sizes.
3. Click **Download .icns** to get a binary ICNS file you can use directly.
4. Optionally, click **Download .iconset ZIP** to get an `AppIcon.iconset` folder
   compatible with Xcode and `iconutil`.

## What it generates

| OSType | Size      | Role                    |
|--------|-----------|-------------------------|
| icp4   | 16×16     | Sidebar / small labels  |
| icp5   | 32×32     | Retina 16@2x            |
| icp6   | 64×64     | Retina 32@2x            |
| ic07   | 128×128   | Standard medium         |
| ic08   | 256×256   | Standard large          |
| ic09   | 512×512   | Finder / Dock           |
| ic10   | 1024×1024 | App Store / 512@2x      |

## How to use the .icns file

### Assign to a .app bundle
1. In Finder, right-click your `.app` → **Get Info**.
2. Click the icon in the top-left of the info window.
3. Paste (`⌘V`) — or drag your `.icns` file onto it.

### Use in an Xcode project
Drag the `.icns` into your asset catalog's AppIcon set, or place it directly in
the project and reference it via the `CFBundleIconFile` key in `Info.plist`.

### Convert the .iconset ZIP manually
```bash
unzip AppIcon.iconset.zip
iconutil -c icns AppIcon.iconset
# → AppIcon.icns
```

## How it works

Everything runs in the browser:

1. **SVG → Canvas** — `new Image()` loads the SVG data URL; `drawImage` renders it
   at each target size onto an off-screen `<canvas>`. Because SVG is vector, every
   size is crisp with no quality loss.

2. **Canvas → PNG bytes** — `canvas.toBlob('image/png')` extracts raw PNG data as a
   `Uint8Array`.

3. **PNG bytes → ICNS** — A `DataView` writes the ICNS binary format:
   - 8-byte file header (`icns` magic + total file size, big-endian)
   - Per-icon entries: 4-byte OSType + 4-byte entry length + raw PNG payload

4. **Download** — A Blob URL triggers the browser's native file-save dialog.

No file is sent to any server.

## Dependencies

- **JSZip** (CDN, for the optional iconset ZIP export only) — not needed for `.icns`
  generation.

## Limitations

- SVGs that load external resources (fonts, remote images) may render blank due to
  browser security restrictions on canvas `drawImage`. Self-contained SVGs work fine.
- The `.iconset` ZIP option requires an internet connection to load JSZip from CDN on
  first use. The `.icns` download has no external dependency.
