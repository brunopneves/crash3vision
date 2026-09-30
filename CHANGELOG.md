# Changelog

## [1.0.0]

First public source-available release.

### Fixed
- Correct the README architecture paths for the CRASH3 controller and application assets.
- Separate runtime and build requirements and remove unused NumPy/OpenCV/Matplotlib declarations, preserving the app/requirements.txt build entry point.
- Include extensionless license/notice files and application PNG/ICO assets in AI bundles, respecting directory exclusions regardless of case.
- Restore structural-reference offset fields into the active canvas state, including absent values.
- Synchronize W, intervals, Ci and calculation results when W is cleared, preserving calibration.
- Reset transient tools and synchronize alignment locking and controls after successful project loading, preserving restored measurements.
- Prepare project images before replacing the open project; abort on image failure and remove old image slots on successful loads.
- Invalidate NHTSA dialog results when calculation inputs change, preserving initial snapshots and descriptive edits.
- Reject nonpositive NHTSA A/B results in the dialog, clearing previous results and disabling apply/save without changing the base calculation.
- Reject explicit unknown CRASH3 unit markers before replacing the open project; retain SI and legacy conversions, including projects without a marker.
- Invalidate energy/EES when A, B or alpha changes, and only EES when mass changes; preserve saved results during project restoration.
- Restore the workflow stage when reopening projects with only one image.
- Use a shared application version for PT/EN window titles and the Windows application ID.

### Added
- Discreet single-image mode notice in the summary (Portuguese/English).
- Regression tests for image-slot combinations, restored controls, JSON loading, and the notice.

## [0.99] - 2026-05-26

### Added
- Single image mode: loading only one image now enables the alignment panel immediately, allowing the workflow to proceed without a reference image
- Confirmation dialog when attempting to finish alignment with only one image loaded
- Public release repository setup (README and LICENSE for `brunopneves/crash3vision`)

### Fixed
- `cmb_class` (generic stiffness class combo) not being reset when creating a new project
- `txt_A` and `txt_B` not being set to editable when resetting to manual entry on new project
- Tooltip in A/B source label showing speeds in m/s instead of km/h
- Dead import `add_record` removed from `calc_panel.py`
- `render_crossmember_line` creating a new QPen on every call instead of reusing pre-configured pen

### Improved
- A/B source tooltip now shows speeds in km/h consistent with the rest of the UI
- A/B source tooltip now shows units for A (N/m) and B (N/m²)

---

## [0.98] - 2026-05-25

### Changed
- App renamed from **Crash3 MVP** to **Crash3Vision**
- User data directory migrated from `.crash3mvp/` to `.crash3vision/` with automatic legacy migration

### Added
- Welcome screen image displayed on canvas when no project is loaded
- Automatic migration of user library from `.crash3mvp/` to `.crash3vision/` on first launch
- `build.py` script for automated build with PyArmor obfuscation + PyInstaller packaging
- `requirements.txt` with project dependencies
- `README.md` with full project documentation, methodology, and validation results
- `.gitignore` updated for PyArmor and build artifacts
- Warning in exported report when project is incomplete (energy or speed not yet calculated)

### Fixed
- `ctypes.windll` call without platform guard — now only runs on Windows
- Duplicate `"b1"` key in A/B file export (`_on_export_ab_file`) — `b0` was being silently lost
- Missing i18n key `nhtsa.error.c_gt_L` — validation message was showing raw key string
- Inconsistent speed units in NHTSA dialog — `_on_compute` was displaying m/s while `_update_derived_speeds` displayed km/h
- Missing `"units"` field in `stiffness_library.json` — conversion intent was implicit and fragile
- `txt_A` / `txt_B` fields not restoring read-only state and `cmb_class` selection after project load
- `_on_save` in `NhtsaAbDialog` using `add_record` on bundled file instead of `upsert_record` on user library — caused duplicates with `_1`, `_2` suffixes
- Vehicle mass (`txt_vehicle_mass`) not auto-filled when loading record from A/B library or importing A/B file
- Report generator displaying NHTSA test speeds in m/s instead of km/h
- EES result lines in report lacking explicit label
- A/B library showing stale records after bundled file update

### Improved
- Report now shows all NHTSA test speeds converted to km/h for consistency with UI
- EES result labeled explicitly as `EES (m/s)` and `EES (km/h)` in report
- `upsert_record` now used throughout to prevent duplicate library entries

---

## [0.97] - 2026-05-18

### Changed
- NHTSA A/B dialog now accepts impact speed and test velocity change in km/h, while preserving internal calculations and storage in m/s.

### Added
- Visual crush profile overlay connecting the upper endpoints of C1-C6 after marking completion.

### Improved
- Enhanced visual feedback for deformation consistency during marking.
- Better user support for identifying inconsistencies in Ci measurements.

## [0.95] - 2026-04-01
### Added
- Support for NHTSA A/B computation using either impact speed or damage speed.
- Derived speed fields: impact speed, velocity change, rebound speed, and damage speed.
- Import/export of A/B records as individual JSON files.
- Reporting of NHTSA speed basis and derived speed values.
- Tooltip enrichment for A/B source metadata.

### Changed
- Improved workflow behavior after loading completed projects.
- Updated A/B source handling for library, file, report, generic class, and manual modes.
- Improved persistence of NHTSA-derived metadata and bumper crossmember offset.

### Fixed
- Workflow controls remaining disabled after loading a completed project.
- Translation inconsistencies related to NHTSA and offset fields.
- State restoration issues for offset and A/B metadata.

## [0.94] - 2026-03-19
### Added
- Import/export support for individual NHTSA A/B JSON files
- New A/B source type for imported files

### Changed
- Replaced direct A/B load button with cleaner Library / A/B files menu
- Improved calc panel UX for NHTSA-related actions

## [0.93] - 2026-03-19
### Added
- Dynamic project name in main window title
- Executable/window icon support for distribution

### Fixed
- Calibration distance restoration after loading project
- NHTSA snapshot consistency when loading/editing A/B
- Allow zero values in C1..C6 validation
- UI resizing and label wrapping issues
- Resource path handling for PyInstaller builds

## [0.92]
### Added
- Improved report structure with methodology section
- Extended i18n support for report

### Fixed
- Calibration state restoration (px and meters)
- NHTSA library loading (multiple entries issue)
- Allow zero values for C1..C6
- Dialog resizing and layout overflow issues
- Project reload inconsistencies (A/B source and snapshot)

## [0.91]
### Added
- Input validation for NHTSA A/B computation dialog
- Support for storing extended NHTSA metadata in library records
- Reopen/edit workflow for saved NHTSA A/B snapshot data
- Automatic restoration of A/B source UI after project load

### Fixed
- A/B source state not being restored correctly after loading projects
- Manual/source overwrites during recalculation
- Inconsistencies between NHTSA snapshot data and project state
- Translation keys missing from grouped calc panel titles

## [0.90]
### Added
- NHTSA A/B computation dialog (full workflow)
- A/B source tracking (manual, generic class, NHTSA library, NHTSA report)
- Tooltip with detailed NHTSA test information
- Persistence of A/B source and metadata in project JSON

### Fixed
- cm to m migration issues in multiple modules
- Load project restoring incorrect A/B source state
- UI inconsistencies after loading saved projects

## [0.86]
### Changed
- Measurement units migrated from centimeters to meters in GUI and saved files

### Fixed
- Project load issues after migration from cm to m
- Remaining references to old geometry fields

## [0.85]
- PT/EN translation coverage expanded
- Metric display standardized to meters

## [0.84]
### Added
- Horizontal guide line tool
- Export report (.txt) feature
- Internationalization system (i18n) — English and Portuguese

## [0.83]
### Changed
- Direct selection of C1-C6 using radio buttons
- Extended CRASH3 energy formulation implemented
- Full migration to SI units (A N/m, B N/m2)

## [0.82]
- Extended CRASH3 energy formula implemented
- Angular correction alpha added

## [0.81]
- Reference image transform support
- Keyboard shortcuts for alignment

## [0.80]
- Damage speed calculation from energy
- PNG chart export

## [0.60]
- CRASH3 energy calculation
- Generic stiffness class library
- Workflow stage gating

## [0.50]
- W measurement, slice generation, C1-C6 measurement

## [0.40]
- Alignment, calibration, project save/load, overlay export
