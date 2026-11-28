"""Stage a Windows release, then promote it after functional validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import runpy
import shutil
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from build_installer import build_installer, check_bundle, find_compiler
from build_windows import ROOT, build


EXAMPLE = "nhtsa_jeep_compass_2024_m20240300"
PROJECT = "crash3vision_reference_project.json"
FRAMES = ("reference_vehicle_frame_000.png", "deformed_vehicle_frame_300.png")
EXAMPLE_FILES = (PROJECT, *FRAMES, "README.md", "crash3vision-example.png")
GENERATED = re.compile(r"CRASH3Vision-v\d+\.\d+\.\d+-Windows-x64(?:[-.][\w.-]+)?", re.I)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tree_files(path: Path):
    if path.is_symlink() or path.is_junction():
        raise ValueError(f"Refusing to traverse a link: {path}")
    if path.is_dir():
        for child in sorted(path.iterdir()):
            yield from tree_files(child)
    elif path.is_file():
        yield path
    else:
        raise ValueError(f"Unsupported path: {path}")


def write_hash(path: Path) -> None:
    path.with_name(path.name + ".sha256").write_text(
        f"{digest(path)}  {path.name}\n", encoding="ascii"
    )


def check_hash(path: Path) -> None:
    record = path.with_name(path.name + ".sha256").read_text(encoding="ascii").split()
    if record != [digest(path), path.name]:
        raise ValueError(f"Invalid SHA-256 record: {path}")


def check_example(bundle: Path) -> None:
    folder = bundle / "examples" / EXAMPLE
    data = json.loads((folder / PROJECT).read_text(encoding="utf-8"))
    for key, name in zip(("ref_path", "dam_path"), FRAMES, strict=True):
        if data.get(key) != name or not (folder / name).is_file():
            raise ValueError(f"Compass project has a missing or nonportable {key}.")


def prepare(stage: Path, stem: str, version: str, args: argparse.Namespace) -> None:
    compiler = find_compiler(args.iscc)
    if compiler is None:
        raise ValueError("Pass --iscc with the path to an Inno Setup compiler.")
    qt_sources = args.qt_sources or ROOT / "dist" / f"{stem}-Qt-sources.zip"
    check_hash(qt_sources)
    stage.mkdir(parents=True)
    bundle = stage / stem
    if args.reuse_portable:
        source = args.reuse_portable.resolve(strict=True)
        check_bundle(source)
        list(tree_files(source))
        shutil.copytree(source, bundle, ignore=shutil.ignore_patterns("THIRD_PARTY_NOTICES"))
        shutil.copy2(ROOT / "THIRD_PARTY_NOTICES", bundle)
    else:
        build(lean=True, destination=bundle)
    check_bundle(bundle)
    sample = bundle / "examples" / EXAMPLE
    sample.mkdir(parents=True)
    example_source = ROOT / "examples" / EXAMPLE
    for name in EXAMPLE_FILES:
        if name != "README.md":
            shutil.copy2(example_source / name, sample / name)
    check_example(bundle)
    readme = sample / "README.md"
    readme.write_text(
        (example_source / "README.md").read_text(encoding="utf-8")
        + "\n## Using the bundled example / Uso do exemplo incluído\n\n"
        "Open the JSON via **File → Open project**. Use **Save project (.json)** and "
        "choose a path in your personal folder before editing. To move the example and its "
        "images together, copy this entire folder first.\n\n"
        "Abra o JSON em **Arquivo → Abrir projeto**. Use **Salvar projeto (.json)** "
        "e selecione um caminho em sua pasta pessoal antes de editar. Para mover "
        "o projeto junto com as imagens, copie primeiro toda esta pasta.\n",
        encoding="utf-8",
    )
    (bundle / "docs").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "docs/windows-lean-compliance.md", bundle / "docs")
    source_copy = stage / f"{stem}-Qt-sources.zip"
    shutil.copy2(qt_sources, source_copy)
    write_hash(source_copy)
    with ZipFile(source_copy) as sources:
        for member in sources.infolist():
            if member.is_dir() or not member.filename.startswith("qt-source-attributions/"):
                continue
            target = bundle / "licenses" / "Qt" / member.filename
            if not target.resolve().is_relative_to((bundle / "licenses" / "Qt").resolve()):
                raise ValueError(f"Unexpected attribution path: {member.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(sources.read(member))
    portable = stage / f"{stem}.zip"
    with ZipFile(portable, "x", ZIP_DEFLATED) as archive:
        for file in tree_files(bundle):
            archive.write(file, file.relative_to(stage).as_posix())
    verify_zip(portable, bundle)
    installer = stage / f"{stem}-Setup.exe"
    build_installer(version, bundle, compiler, installer)
    for artifact in (portable, installer):
        write_hash(artifact)
    receipts = {p.relative_to(stage).as_posix(): digest(p) for p in tree_files(stage)}
    (stage / "ready.json").write_text(json.dumps(receipts, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {stage}. Validate the staged installer before running publish.")


def verify_zip(path: Path, bundle: Path) -> None:
    files = {p.relative_to(bundle.parent).as_posix(): p for p in tree_files(bundle)}
    with ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(files) or set(names) != files.keys():
            raise ValueError("Portable ZIP contents differ from the staged directory.")
        for name, file in files.items():
            with archive.open(name) as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != digest(file):
                    raise ValueError(f"Portable ZIP differs from the staged file: {name}")


def publish(stage: Path, dist: Path, stem: str) -> None:
    # Validate the complete stage before moving or deleting any existing output.
    receipt = stage / "ready.json"
    expected = json.loads(receipt.read_text(encoding="utf-8"))
    actual = {p.relative_to(stage).as_posix(): digest(p) for p in tree_files(stage) if p != receipt}
    if actual != expected:
        raise ValueError("Staged files have changed since preparation.")
    artifact_names = [f"{stem}.zip", f"{stem}-Setup.exe", f"{stem}-Qt-sources.zip"]
    names = {stem, *artifact_names, *(name + ".sha256" for name in artifact_names)}
    if {p.name for p in stage.iterdir()} != names | {receipt.name}:
        raise ValueError("Staging contains unexpected outputs.")
    for artifact in artifact_names:
        check_hash(stage / artifact)
    check_example(stage / stem)
    if (ROOT / ".git").exists():
        tracked = subprocess.check_output(["git", "ls-files", "--", "dist"], cwd=ROOT)
        if tracked:
            raise ValueError("Refusing to clean dist because it contains tracked files.")
    dist.mkdir(exist_ok=True)
    if dist.is_symlink() or dist.is_junction() or dist.resolve() != ROOT / "dist":
        raise ValueError("dist must be a local directory in the repository.")
    old = sorted(dist.iterdir())
    for item in old:
        if not (GENERATED.fullmatch(item.name) or item.name == "_archive"
                or item.suffix.lower() in {".log", ".tmp", ".spec", ".sha256"}):
            raise ValueError(f"Refusing to discard unrecognized output: {item}")
        list(tree_files(item))

    backup = dist / ".release-rollback"
    moved = []
    promoted = []
    backup.mkdir()
    try:
        for item in old:
            item.rename(backup / item.name)
            moved.append(item)
        for name in sorted(names):
            source = stage / name
            target = dist / name
            promoted.append(target)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
        for artifact in artifact_names:
            check_hash(dist / artifact)
        check_example(dist / stem)
        verify_zip(dist / f"{stem}.zip", dist / stem)
    except (Exception, KeyboardInterrupt):
        for target in reversed(promoted):
            if target.resolve().parent != dist or target.is_symlink() or target.is_junction():
                raise ValueError(f"Unsafe partial output: {target}")
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)
        for item in reversed(moved):
            (backup / item.name).rename(item)
        backup.rmdir()
        raise
    if backup.resolve().parent != dist or backup.is_symlink() or backup.is_junction():
        raise ValueError("Unsafe rollback directory.")
    list(tree_files(backup))
    shutil.rmtree(backup)
    # Keep the stage intact until promotion and rollback cleanup have succeeded.
    for item in stage.iterdir():
        if item.resolve().parent != stage or item.is_symlink() or item.is_junction():
            raise ValueError(f"Unsafe staged output: {item}")
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    stage.rmdir()
    print(f"Published locally: {dist}. Removed {len(old)} replaced or obsolete outputs.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    staging = commands.add_parser("prepare")
    staging.add_argument("--iscc", type=Path)
    staging.add_argument("--reuse-portable", type=Path)
    staging.add_argument("--qt-sources", type=Path)
    promotion = commands.add_parser("publish")
    promotion.add_argument("--validated", action="store_true", required=True,
                           help="Confirm the staged artifacts passed functional validation.")
    args = parser.parse_args()
    version = runpy.run_path(str(ROOT / "app/version.py"))["__version__"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        parser.error("Expected a three-part Windows release version.")
    stem = f"CRASH3Vision-v{version}-Windows-x64"
    stage = ROOT / "build" / "windows" / f"{stem}-release-stage"
    if stage.resolve() != stage:
        parser.error("Staging directory must be local to the repository.")
    try:
        if args.action == "prepare":
            prepare(stage, stem, version, args)
        else:
            publish(stage, ROOT / "dist", stem)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Windows release failed: {error}\n")


if __name__ == "__main__":
    main()
