"""Build the portable CRASH3Vision package from the active Windows x64 environment."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import os
import platform
import runpy
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "CRASH3Vision"
RUNTIME_ASSETS = (
    "app/assets/crash3_icon.ico",
    "app/assets/welcome.png",
    "app/assets/crash3_energy.svg",
    "app/assets/crash3_energy_compact.svg",
    "app/assets/crash3_energy_terms.svg",
    "app/assets/crash3_ees.svg",
    "app/data/nhtsa_ab_library.json",
    "app/data/stiffness_library.json",
)
PACKAGES = (
    "PySide6", "PySide6-Essentials", "PySide6-Addons", "shiboken6",
    "numpy", "opencv-python-headless", "PyInstaller", "pyinstaller-hooks-contrib",
)
LEAN_PACKAGES = tuple(name for name in PACKAGES if name not in {"PySide6", "PySide6-Addons"})
LEAN_EXCLUDES = ("PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtNetwork", "_ssl", "_hashlib")
LEAN_UNUSED_DLLS = {
    "opengl32sw.dll", "qpdf.dll", "qt6pdf.dll", "qt6pdfwidgets.dll", "qt6network.dll",
    "qdirect2d.dll", "qminimal.dll", "qcertonlybackend.dll",
    "qopensslbackend.dll", "qschannelbackend.dll", "qnetworklistmanager.dll",
    "qtuiotouchplugin.dll",
}


def write_version_info(path: Path, version: str) -> None:
    major, minor, patch = map(int, version.split("."))
    numbers = (major, minor, patch, 0)
    path.write_text(
        f"""VSVersionInfo(
    ffi=FixedFileInfo(filevers={numbers}, prodvers={numbers}, mask=0x3f,
        flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('FileDescription', '{APP_NAME}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('ProductName', '{APP_NAME}'),
        StringStruct('ProductVersion', '{version}'),
        StringStruct('OriginalFilename', '{APP_NAME}.exe'),
    ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
""",
        encoding="utf-8",
    )


def copy_notices(bundle: Path, packages: tuple[str, ...] = PACKAGES) -> None:
    for name in ("LICENSE", "THIRD_PARTY_NOTICES"):
        shutil.copy2(ROOT / name, bundle / name)

    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise RuntimeError("CPython LICENSE.txt was not found in the base Python installation.")
    license_dir = bundle / "licenses"
    python_dir = license_dir / "CPython"
    python_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(python_license, python_dir)
    qt_dir = license_dir / "Qt"
    qt_dir.mkdir(exist_ok=True)
    for name in ("GPL-3.0-only", "LGPL-3.0-only"):
        shutil.copy2(ROOT / "scripts" / "licenses" / name, qt_dir / f"{name}.txt")

    native_files = sorted(
        item.relative_to(bundle).as_posix()
        for item in bundle.rglob("*")
        if item.suffix.lower() in {".dll", ".pyd", ".exe"}
    )
    if any(Path(item).name.lower().startswith(("libssl-3", "libcrypto-3")) for item in native_files):
        openssl_dir = license_dir / "OpenSSL"
        openssl_dir.mkdir(exist_ok=True)
        shutil.copy2(ROOT / "scripts/licenses/OpenSSL-3-Apache-2.0", openssl_dir / "LICENSE.txt")
    packaged_qt = {
        item.removeprefix("_internal/").lower()
        for item in native_files
        if item.startswith("_internal/PySide6/")
    }
    distributions = {name: metadata.distribution(name) for name in packages}
    known = {name.lower().replace("_", "-") for name in packages}
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        normalized = name.lower().replace("_", "-")
        if not normalized.startswith("pyside6-") or normalized in known:
            continue
        if any(item.as_posix().lower() in packaged_qt for item in (dist.files or ())):
            distributions[name] = dist
    versions = [f"Python {platform.python_version()}"]
    for package, dist in distributions.items():
        versions.append(f"{package} {dist.version}")
        files = [
            (item, item.parts.index(part))
            for item in (dist.files or ())
            for part in item.parts
            if part.endswith(".dist-info") and (
                "licenses" in item.parts[item.parts.index(part) + 1:]
                or item.name.upper().startswith(("LICENSE", "COPYING", "NOTICE"))
            )
        ]
        if not files:
            raise RuntimeError(f"No wheel license files found for {package}.")
        for item, index in files:
            target = license_dir.joinpath(package, *item.parts[index + 1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dist.locate_file(item), target)

    (bundle / "BUILD_INFO.txt").write_text(
        "Build environment\n" + "\n".join(versions)
        + "\n\nPackaged native files\n" + "\n".join(native_files) + "\n",
        encoding="utf-8",
    )


def trim_lean_bundle(bundle: Path) -> None:
    import pefile

    native_files = [path for path in bundle.rglob("*") if path.suffix.lower() in {".dll", ".pyd", ".exe"}]
    removed = {
        path for path in native_files
        if path.name.lower() in LEAN_UNUSED_DLLS
        or path.name.lower().startswith(("opencv_videoio_ffmpeg", "libssl-3", "libcrypto-3"))
    }
    removed_names = {path.name.lower() for path in removed}
    for path in native_files:
        if path in removed:
            continue
        with pefile.PE(str(path), fast_load=True) as binary:
            binary.parse_data_directories(directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
            ])
            for field in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT"):
                for entry in getattr(binary, field, ()):
                    name = entry.dll.decode("ascii").lower()
                    if name in removed_names:
                        raise RuntimeError(f"{path.relative_to(bundle)} depends on excluded {name}.")
    for path in sorted(removed):
        print(f"Exclude {path.relative_to(bundle)} ({path.stat().st_size:,} bytes)")
        path.unlink()


def build(*, lean: bool = False, destination: Path | None = None) -> Path:
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"} or struct.calcsize("P") != 8:
        raise RuntimeError("Run the build with a Windows x64 Python interpreter.")
    packages = LEAN_PACKAGES if lean else PACKAGES
    for package in packages:
        metadata.version(package)
    version = runpy.run_path(str(ROOT / "app/version.py"))["__version__"]
    variant = "-lean" if lean else ""
    destination = destination or ROOT / "dist" / f"{APP_NAME}-v{version}-Windows-x64{variant}"
    if destination.exists():
        raise RuntimeError(f"Move the existing build before rebuilding: {destination}")
    for relative in RUNTIME_ASSETS:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"Required runtime asset is missing: {relative}")

    work = ROOT / "build" / "windows" / "lean" if lean else ROOT / "build" / "windows"
    work.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="package-", dir=work) as folder:
        staging = Path(folder)
        version_info = staging / "version.txt"
        write_version_info(version_info, version)
        hooks = staging / "hooks"
        hooks.mkdir()
        # QtGui collects input-context plugins by default. The unused Qt Virtual
        # Keyboard is GPLv3/commercial, outside the intended LGPL Qt set.
        (hooks / "hook-PySide6.QtGui.py").write_text(
            '''from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
binaries = [
    (source, target) for source, target in binaries
    if Path(source).name.lower() != "qtvirtualkeyboardplugin.dll"
]
''',
            encoding="utf-8",
        )
        command = [
            sys.executable, "-m", "PyInstaller",
            "--onedir", "--windowed", "--noupx", "--name", APP_NAME,
            "--distpath", str(staging / "dist"), "--workpath", str(work / "pyinstaller"),
            "--specpath", str(staging), "--paths", str(ROOT),
            "--additional-hooks-dir", str(hooks),
            "--icon", str(ROOT / "app/assets/crash3_icon.ico"), "--version-file", str(version_info),
        ]
        for relative in RUNTIME_ASSETS:
            command.extend(("--add-data", f"{ROOT / relative}:{Path(relative).parent.as_posix()}"))
        if lean:
            for module in LEAN_EXCLUDES:
                command.extend(("--exclude-module", module))
        env = os.environ.copy()
        env.setdefault("PYINSTALLER_CONFIG_DIR", str(work / "cache"))
        subprocess.run([*command, str(ROOT / "app/main.py")], cwd=ROOT, env=env, check=True)
        bundle = staging / "dist" / APP_NAME
        if not (bundle / f"{APP_NAME}.exe").is_file():
            raise RuntimeError("PyInstaller did not create the executable.")
        if not any(bundle.rglob("qwindows.dll")):
            raise RuntimeError("The Windows Qt platform plugin is missing.")
        if any("virtualkeyboard" in item.name.lower() for item in bundle.rglob("*.dll")):
            raise RuntimeError("The unused Qt Virtual Keyboard was collected into the package.")
        for relative in RUNTIME_ASSETS:
            if not (bundle / "_internal" / relative).is_file():
                raise RuntimeError(f"PyInstaller omitted {relative}.")
        if lean:
            trim_lean_bundle(bundle)
        copy_notices(bundle, packages)
        destination.parent.mkdir(exist_ok=True)
        shutil.copytree(bundle, destination)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", action="store_true", help="Build the still-image desktop profile in a separate folder.")
    try:
        print(f"Built: {build(lean=parser.parse_args().lean)}")
    except metadata.PackageNotFoundError as error:
        sys.exit(f"Missing build dependency: {error.name}. Install requirements.txt and PyInstaller.")
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"Windows build failed: {error}")
