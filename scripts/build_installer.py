"""Validate the portable bundle and compile the Windows installer with an existing ISCC."""

from __future__ import annotations

import argparse
import os
import re
import runpy
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "windows_installer.iss"
REQUIRED_FILES = (
    "CRASH3Vision.exe", "LICENSE", "THIRD_PARTY_NOTICES", "BUILD_INFO.txt",
    "_internal/PySide6/plugins/platforms/qwindows.dll",
    "_internal/app/assets/crash3_icon.ico",
    "_internal/app/assets/welcome.png",
    "_internal/app/assets/crash3_ees.svg",
    "_internal/app/assets/crash3_energy.svg",
    "_internal/app/assets/crash3_energy_compact.svg",
    "_internal/app/assets/crash3_energy_terms.svg",
    "_internal/app/data/nhtsa_ab_library.json",
    "_internal/app/data/stiffness_library.json",
    "licenses/Qt/LGPL-3.0-only.txt",
    "licenses/Qt/GPL-3.0-only.txt",
)


def find_compiler(explicit: Path | None) -> Path | None:
    if explicit is not None:
        if not explicit.is_file():
            raise ValueError(f"ISCC.exe was not found at {explicit}.")
        return explicit.resolve()
    located = shutil.which("ISCC.exe")
    if located:
        return Path(located)
    for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        location = os.environ.get(variable)
        if location:
            directory = Path(location)
            if variable == "LOCALAPPDATA":
                directory /= "Programs"
            candidate = directory / "Inno Setup 6" / "ISCC.exe"
            if candidate.is_file():
                return candidate
    return None


def build_installer(version: str, bundle: Path, compiler: Path, destination: Path) -> None:
    if destination.exists():
        raise ValueError(f"Move the existing installer before compiling: {destination}")
    subprocess.run(
        [
            str(compiler), f"--define=ReleaseVersion={version}", f"--define=BundleDir={bundle}",
            f"--define=OutputStem={destination.stem}", f"--output-dir={destination.parent}",
            str(SCRIPT),
        ],
        cwd=ROOT, check=True,
    )
    if not destination.is_file():
        raise ValueError(f"The compiler did not produce {destination}.")


def check_bundle(bundle: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (bundle / name).is_file()]
    if missing:
        raise ValueError(f"Incomplete portable bundle {bundle}. Missing: {', '.join(missing)}")
    if any("virtualkeyboard" in path.name.lower() for path in bundle.rglob("*.dll")):
        raise ValueError("The portable bundle contains the unused Qt Virtual Keyboard.")
    for path in (SCRIPT, ROOT / "app/assets/crash3_icon.ico", ROOT / "docs/windows-installer.md"):
        if not path.is_file():
            raise ValueError(f"Missing installer input: {path}")


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iscc", type=Path, help="Path to an existing Inno Setup 6 compiler.")
    parser.add_argument("--check", action="store_true", help="Check inputs without compiling.")
    parser.add_argument("--lean", action="store_true", help="Package the separate portable candidate.")
    args = parser.parse_args()

    version = runpy.run_path(str(ROOT / "app/version.py"))["__version__"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"Expected a three-part Windows release version, got {version!r}.")
    variant = "-lean" if args.lean else ""
    stem = f"CRASH3Vision-v{version}-Windows-x64{variant}"
    bundle = ROOT / "dist" / stem
    check_bundle(bundle)

    compiler = find_compiler(args.iscc)
    print(f"Portable bundle inputs verified for {stem}.")
    if args.check:
        print(f"Inno Setup: {compiler}" if compiler else "Inno Setup not found; compilation was not run.")
        return
    if compiler is None:
        raise ValueError("Inno Setup 6 is required. Use --iscc to select an existing ISCC.exe.")
    destination = ROOT / "dist" / f"{stem}-Setup.exe"
    build_installer(version, bundle, compiler, destination)
    print(f"Built: {destination}")


if __name__ == "__main__":
    try:
        run()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"Windows installer build failed: {error}")
