# FileMaker Launcher

A native macOS `.app` that silently opens an embedded FileMaker solution file
(`.fmpsl`) using the highest compatible FileMaker version installed on the
machine. No UI. Compatible with FileMaker Pro / FileMaker Pro Advanced 16, 17,
and 18.

## How it works

`FileMakerLauncher.app` is a hand-crafted `.app` bundle — a directory structure
macOS recognises as an application, with no Xcode project or Cocoa runtime
required. When double-clicked, macOS executes the shell script at
`Contents/MacOS/launcher`.

The script:
1. Scans `/Applications` for FileMaker Pro [16|17|18].app in descending order
2. Picks the highest version found (regular variant preferred over Advanced for
   the same version number)
3. Calls `open -a "$fm_app" "$fmpsl"` to open the embedded solution
4. On failure, shows a native macOS alert via `osascript`

`LSUIElement = true` in `Info.plist` prevents a Dock icon from appearing during
the brief script execution.

## Bundle structure

````
FileMakerLauncher.app/
└── Contents/
    ├── Info.plist            ← app metadata
    ├── MacOS/
    │   └── launcher          ← shell script (executable)
    └── Resources/
        ├── solution.fmpsl    ← your FileMaker shortcut file
        └── AppIcon.icns      ← your app icon
````

## Customising for distribution

1. Place your `solution.fmpsl` file next to `build.sh`
2. Place your `AppIcon.icns` file next to `build.sh`
3. Edit `Info.plist` — update `CFBundleIdentifier` to your organisation's
   reverse domain (e.g. `com.acme.my-solution`)
4. Run `bash build.sh` to assemble the bundle
5. Distribute `FileMakerLauncher.app`

## Compatibility

| FileMaker version | Detected app names |
|-------------------|--------------------|
| 18                | FileMaker Pro 18.app, FileMaker Pro Advanced 18.app |
| 17                | FileMaker Pro 17.app, FileMaker Pro Advanced 17.app |
| 16                | FileMaker Pro 16.app, FileMaker Pro Advanced 16.app |

## Testing

The detection logic is covered by a pure shell test suite that creates mock
`.app` directories in a temp folder — no FileMaker installation required:

```bash
bash test_launcher.sh
```

## Limitations

- Non-standard install locations (outside `/Applications`) are not supported
- Code signing / notarization is not included — Gatekeeper may block on first
  launch; right-click → Open to bypass
- FileMaker versions outside 16–18 are out of scope
