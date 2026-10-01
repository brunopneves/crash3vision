# Changelog

## [1.0.0]

First public source-available release.

### Added
- Public release of CRASH3Vision as experimental research software.
- Single-image and dual-image analysis workflows.
- Geometric calibration and reference/deformed image alignment.
- Semi-assisted W and C1-C6 deformation measurement.
- Optional bumper crossmember offset visualization.
- CRASH3-derived deformation-energy and EES calculation.
- Manual, generic and NHTSA-related A/B coefficient workflows.
- Project save/load support.
- Technical report export with measurement inputs, coefficient provenance, calculation parameters and results.
- PNG canvas export.
- Portuguese and English interface.
- Public methodology, validation, citation, licensing and third-party documentation.

### Fixed
- Restore structural-reference offset fields into the active canvas state.
- Synchronize W, intervals, Ci and calculation results when W is cleared while preserving calibration.
- Reset transient tools and synchronize alignment controls after successful project loading.
- Prepare project images before replacing the open project and preserve the current project on image-load failure.
- Invalidate stale NHTSA dialog results when calculation inputs change.
- Reject nonpositive NHTSA A/B results in the dialog.
- Reject explicit unknown CRASH3 unit markers before replacing the open project.
- Invalidate energy/EES when A, B or alpha changes, and only EES when mass changes.
- Restore the workflow stage when reopening projects with only one image.
- Use a shared application version for PT/EN window titles and the Windows application ID.

### Improved
- Clarified public documentation for experimental scope, limitations and validation.
- Clarified generic stiffness-library values as illustrative only.
- Added public citation metadata and noncommercial licensing information.

---

## [0.99] - 2026-05-26

### Added
- Single-image mode.
- Confirmation behavior for alignment when only one image is loaded.

### Fixed
- Generic stiffness-class reset behavior when creating a new project.
- A/B field editability when returning to manual entry.
- A/B source tooltip speed units.
- Unused import in the calculation panel.
- Reuse of the configured crossmember rendering pen.

### Improved
- A/B source tooltip now shows speeds in km/h and units for A and B.

---

## [0.98] - 2026-05-25

### Changed
- Application renamed from **Crash3 MVP** to **CRASH3Vision**.
- User data directory migrated from `.crash3mvp/` to `.crash3vision/` with automatic legacy migration.

### Added
- Welcome screen image.
- Automatic migration of the user A/B library.
- Runtime dependency file.
- README documentation with methodology and validation results.
- Warning in exported reports when a project is incomplete.

### Fixed
- Windows-only platform guard for the application identifier.
- Duplicate A/B export key that could omit `b0`.
- Missing internationalization key for NHTSA validation.
- Inconsistent speed display units in the NHTSA dialog.
- Explicit stiffness-library unit marker.
- Restoration of A/B UI state after project load.
- User-library save behavior for NHTSA A/B records.
- Vehicle-mass restoration from A/B records.
- Report speed units and explicit EES labels.
- Refresh behavior for bundled/user A/B libraries.

### Improved
- Reported NHTSA speeds standardized to km/h.
- EES results labeled explicitly in m/s and km/h.
- A/B records updated without unnecessary duplicates.

---

## [0.97] - 2026-05-18

### Changed
- NHTSA A/B dialog accepts impact speed and test velocity change in km/h while preserving internal calculations in m/s.

### Added
- Visual crush-profile overlay connecting the upper endpoints of C1-C6.

### Improved
- Visual feedback for deformation consistency during marking.

## [0.95] - 2026-04-01

### Added
- NHTSA A/B computation using impact speed or damage speed.
- Derived speed fields.
- Import/export of individual A/B records.
- Reporting of NHTSA speed basis and derived speed values.
- A/B source metadata tooltips.

### Changed
- Improved workflow behavior after loading completed projects.
- Expanded A/B source handling and persistence.

### Fixed
- Workflow controls after loading completed projects.
- Translation issues related to NHTSA and offset fields.
- State restoration for offset and A/B metadata.

## [0.94] - 2026-03-19

### Added
- Import/export support for individual NHTSA A/B JSON files.
- New A/B source type for imported files.

### Changed
- Cleaner Library / A/B files menu.
- Improved calculation-panel UX for NHTSA-related actions.

## [0.93] - 2026-03-19

### Added
- Dynamic project name in the main-window title.
- Executable/window icon support.

### Fixed
- Calibration distance restoration after loading a project.
- NHTSA snapshot consistency when loading/editing A/B.
- Zero-value support for C1-C6 validation.
- UI resizing and label wrapping.
- Resource path handling.

## [0.92]

### Added
- Improved report structure with methodology section.
- Extended report internationalization.

### Fixed
- Calibration state restoration.
- NHTSA library loading.
- Zero-value support for C1-C6.
- Dialog resizing and layout overflow.
- Project reload consistency.

## [0.91]

### Added
- Input validation for NHTSA A/B computation.
- Extended NHTSA metadata in library records.
- Reopen/edit workflow for saved NHTSA A/B snapshot data.
- Automatic restoration of A/B source UI after project load.

### Fixed
- A/B source restoration.
- Manual/source overwrites during recalculation.
- NHTSA snapshot/project-state consistency.
- Missing translation keys.

## [0.90]

### Added
- NHTSA A/B computation dialog.
- A/B source tracking.
- NHTSA test-information tooltip.
- Persistence of A/B source and metadata.

### Fixed
- cm-to-m migration issues.
- Project-load A/B source state.
- UI inconsistencies after loading saved projects.

## [0.86]

### Changed
- Measurement units migrated from centimeters to meters in GUI and saved files.

### Fixed
- Project-load issues after unit migration.
- Remaining references to old geometry fields.

## [0.85]
- PT/EN translation coverage expanded.
- Metric display standardized to meters.

## [0.84]

### Added
- Horizontal guide-line tool.
- Text report export.
- Internationalization system (English and Portuguese).

## [0.83]

### Changed
- Direct selection of C1-C6 using radio buttons.
- Extended CRASH3 energy formulation.
- Full migration to SI units.

## [0.82]
- Angular correction alpha added.

## [0.81]
- Reference-image transform support.
- Keyboard shortcuts for alignment.

## [0.80]
- Damage-speed calculation from energy.
- PNG chart export.

## [0.60]
- CRASH3 energy calculation.
- Generic stiffness-class library.
- Workflow-stage gating.

## [0.50]
- W measurement, slice generation and C1-C6 measurement.

## [0.40]
- Alignment, calibration, project save/load and overlay export.
