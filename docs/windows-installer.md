# CRASH3Vision v1.1.0 Windows x64

## Distribution and example

The current Windows x64 release payload is prepared with these names.

- `CRASH3Vision-v1.1.0-Windows-x64.zip` is the portable package.
- `CRASH3Vision-v1.1.0-Windows-x64-Setup.exe` installs the same application payload.
- `CRASH3Vision-v1.1.0-Windows-x64-Qt-sources.zip` is the separate Qt source companion.
- Each artifact has a matching `.sha256` file. The unpacked Windows folder is also kept in `dist/`.

Open `examples/nhtsa_jeep_compass_2024_m20240300/crash3vision_reference_project.json`
from **File ? Open project** in the extracted or installed folder. The two
images are in the same example directory. Use **Save project (.json)** to put a
copy in your personal folder before editing. Copy the entire example folder
if the project and its images need to move together.

## Build and validate before replacing the distribution

Use official CPython 3.14.10 x64, Inno Setup 7.1.1, and a fresh virtual
environment outside Conda. Set the executable paths for the build machine
and run from the repository root. Check each command's exit status before
continuing.

```powershell
$python = 'D:\python\python.exe'
$iscc = 'D:\Inno Setup 7\ISCC.exe'
& $python -m venv build/windows/lean-venv-repro
$buildPython = (Resolve-Path build/windows/lean-venv-repro/Scripts/python.exe).Path
& $buildPython -m pip install --only-binary=:all: -r scripts/requirements-windows-lean.in
& $buildPython -m pip check
$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
$env:QT_QPA_PLATFORM = 'offscreen'
& $buildPython -m unittest discover -s tests
Remove-Item Env:QT_QPA_PLATFORM
& $buildPython scripts/build_release.py prepare --iscc $iscc
```

Supply `--qt-sources <path>` if the verified, version-matched Qt source ZIP
and its SHA-256 file are outside `dist/`. Use `--reuse-portable <path>` when
only packaging changes and the optimized application binary is already
validated. The default build uses PyInstaller `--onedir --windowed --noupx`.

Preparation writes the new portable directory, ZIP, installer and checksums
to `build/windows/CRASH3Vision-v1.1.0-Windows-x64-release-stage/`. Existing
distribution files remain available throughout preparation and testing.
Validate the staged artifacts using the checklist below, then run:

```powershell
& $buildPython scripts/build_release.py publish --validated
```

Promotion rechecks the staged SHA-256 records and the Compass paths before
replacing the distribution. Once promotion succeeds, the script removes
displaced builds and recognized temporary outputs under `dist/`. It rejects
unrecognized entries, Git-tracked files and links instead of deleting them.
Keep build work files and logs under `build/`.

## Keep the validated package profile

- Build from official CPython and the pinned wheels. The earlier Conda
  build collected an additional OpenSSL pair, UCRT and API-set forwarders.
- Keep PySide6 Essentials and Shiboken. The lean profile excludes Qt PDF
  and PDFium, Qt Network and its unused TLS/discovery plugins, unused input
  and platform plugins including Qt Virtual Keyboard and Direct2D, OpenSSL,
  the separate OpenCV FFmpeg video DLL, and the Mesa/LLVM software OpenGL
  DLL. These exclusions are for the current raster and still-image workflow.
- Keep the Windows platform and style, offscreen platform, image and SVG
  codecs, NumPy/OpenBLAS, OpenCV image processing and runtime assets. Use
  the packaged profile and its normal and delay-load PE import checks for
  future changes. Avoid blanket DLL removal, one-file packaging and UPX
  in this build procedure.
- Keep the Microsoft runtime substitution experiment out of the test
  candidate. The app-local REDIST comparison was performed in a temporary
  copy. The official Redistributable alone does not supply the DLL name
  imported by the current NumPy wheel.

## Clean Windows manual test

For a clean Windows 10 or 11 x64 machine or VM, use a standard user account,
no Python or developer tools, and no previous CRASH3Vision installation.

- [ ] Verify the portable ZIP and Setup SHA-256 files. Extract the portable ZIP and start
  `CRASH3Vision.exe` from its extracted folder.
- [ ] Run Setup without elevation. Check the Start menu shortcut, version
  **1.1.0** in Installed apps, and the optional desktop shortcut. Start
  from the Start menu.
- [ ] In the installed app, switch Portuguese/English, open Help and its
  equations, and open the Compass project directly from the bundled example. Check images, calibration and
  C1–C6. Recalculate energy and EES, export PNG and TXT, then save and reopen
  a copy outside the installation directory.
- [ ] Uninstall. Confirm the app entry and shortcuts are gone and that the
  saved project and `%USERPROFILE%\.crash3vision\data` remain. Record the
  Windows version, artifact SHA-256 values and any failures.

## Installer language diagnostics

The standard language picker is enabled at launch because Setup includes
English and Brazilian Portuguese. Inno Setup uses the previous installation
language as its default when available. These startup options do not
configure a return to the picker during the wizard. If a return is observed,
run Setup interactively with `/LOG` and record the last completed page and
whether another Setup process started. The `/LANG=pt` and `/LANG=en` options
are useful for isolated automation and bypass the normal picker.

## Microsoft redistribution authorization remains pending

The current artifacts are for internal testing. Authorization for
redistribution of the Microsoft runtimes and the applicable downstream
terms will be resolved separately. Keep this decision independent of the
clean Windows test result. See the [lean distribution compliance record](windows-lean-compliance.md).
