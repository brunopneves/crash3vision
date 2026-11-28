# Windows x64 v1.1.0 lean distribution compliance

The original runtime review covered `CRASH3Vision-v1.1.0-Windows-x64-lean.zip` (SHA-256
`804781aeefbccfe506c622643f0359e90ea769497c9defc8df458155105593a7`) and
`CRASH3Vision-v1.1.0-Windows-x64-lean-Setup.exe` (SHA-256
`8f03fe4da1d23fa9676d8b3163b334340848a889d17c567cc39eb3d29969607f`).
The final-name v1.1.0 packages reuse that application binary and runtime
payload and add the Compass example and attribution material. The Microsoft
authorization pending below applies to the final-name packages.

## Qt source and attribution materials

The binary inventory contains Qt Core, GUI, Widgets, SVG, and the Windows,
offscreen, modern Windows style and retained image/icon plugins. Qt Core
reports Qt 6.12.0, shared x64 release, built by MSVC 2022. The PySide6 Essentials
and Shiboken wheels report 6.12.0 and build timestamps of 2026-10-05 13:28:34 UTC
and 13:28:25 UTC, respectively. The following sources were obtained from Qt
and checked against Qt's published SHA-256 files.

| Payload | Official source archive | Public release revision |
| --- | --- | --- |
| Qt Core, GUI, Widgets, platform and style plugins, built-in codecs and Qt base image plugins | [qtbase 6.12.0](https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtbase-everywhere-src-6.12.0.tar.xz) | `025bdad181de241e81bf853c8a2d7bf3d19261a9` |
| Qt SVG and SVG image/icon plugins | [qtsvg 6.12.0](https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtsvg-everywhere-src-6.12.0.tar.xz) | `883a58532078d003cefef0a549bfe9f885ce41f5` |
| ICNS, TGA, TIFF, WBMP and WebP plugins | [qtimageformats 6.12.0](https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtimageformats-everywhere-src-6.12.0.tar.xz) | `dc13f2fbff1d579cfb2eb2d9092e3563b4d05b8e` |
| PySide6 and Shiboken bindings and runtimes | [pyside-setup 6.12.0](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz) | [`f50facb83fc3dc5f3240c854668c7a6dd93871b2`](https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.12.0) |

The three Qt framework archives identify the source commits in their `.tag`
files. The PySide source includes `setup.py`, binding generator sources, CMake
files and Qt's COIN build instructions. Its `coin/product_dependencies.yaml`
specifies Qt `6.12.0`. Use the [official Windows build procedure](https://doc.qt.io/qtforpython-6/building_from_source/windows.html)
with MSVC x64, a compatible Qt build, the CPython limited ABI (the wheel tag
is `cp310-abi3-win_amd64`), and the LLVM/Clang and other versions verified
against the vendor build configuration.

The local review package includes the upstream archives, checksum evidence,
wheel records, and Qt's source attribution metadata and referenced license
texts. These materials identify the exact **public release revisions**. The
wheel metadata and PE information leave some wheel build details unobserved.
The Qt `qjpeg.dll` reports LibJPEG-turbo 3.2.0, matching the qtbase attribution.
No missing patch, source file or required build script has been identified.
Use these archives as the source companion for the identified releases.
If concrete evidence reveals additional required source, patches or build
scripts, add those materials before conveying the affected binaries. LGPLv3
and GPLv3 do not require a bit-for-bit rebuild or a vendor attestation.

Publish the confirmed corresponding sources with equivalent access alongside
the binary downloads, including the scripts and source/patches needed to
generate, install and run the covered binaries. Retain the GPLv3 and LGPLv3
texts, the prominent Qt/PySide6/Shiboken notices, and the applicable
third-party notices. Provide the collected notices with each binary copy,
including the installer payload. Place the source link next to both binary
downloads and retain access for as long as required by the license. See
[LGPLv3 §4](https://doc.qt.io/qt-6.12/lgpl.html)
and [GPLv3 §6](https://doc.qt.io/qt-6.12/gpl.html).

The release companion is `CRASH3Vision-v1.1.0-Windows-x64-Qt-sources.zip`.
It has its own SHA-256 sidecar and an internal `SHA256SUMS` covering each
source archive, notice, license and metadata file.

## Replacing LGPL libraries

Exit CRASH3Vision. Back up the DLLs and replace the desired build at its
existing relative path, for example `_internal/PySide6/Qt6Svg.dll`. Match x64,
the release ABI and the dependent plugins. Replace the matching `.pyd` and
runtime DLLs together if a PySide6 or Shiboken change requires it. Restart
from the portable or user installation directory and verify the loaded module
paths. Test the relevant functionality, such as opening the Help dialog that
renders SVGs. The installer installs the same application files in a folder
writable by the current user. There is no application DLL signature check
in the installer script. The PolyForm Noncommercial license remains applicable
to the CRASH3Vision code. It does not restrict rights granted by the LGPL,
including reverse engineering to debug modifications to the LGPL libraries.

The native loader test changed the PE checksum field in a temporary copy
of `Qt6Svg.dll`, `pyside6.abi3.dll` and `shiboken6.abi3.dll`. Windows loaded
all three from the copied distribution, and the application started with a
Windows-only PATH. This demonstrates local replacement without an application
integrity check. A functional test using an independently rebuilt,
interface-compatible library is useful validation. The express obligation
is for the shared library mechanism to work with such a library and for
the terms to permit modification and reverse engineering to debug it.

## Microsoft runtimes

| Origin | Versions and filenames |
| --- | --- |
| Official CPython 3.14.10 Windows x64 installation | 14.51.36247.0, `VCRUNTIME140.dll` and `VCRUNTIME140_1.dll` |
| PySide6 Essentials 6.12.0 wheel | 14.44.35211.0, `MSVCP140.dll`, `MSVCP140_1.dll`, `MSVCP140_2.dll`, `VCRUNTIME140.dll` and `VCRUNTIME140_1.dll` |
| Shiboken6 6.12.0 wheel | 14.44.35211.0, `MSVCP140.dll`, `VCRUNTIME140.dll` and `VCRUNTIME140_1.dll` |
| NumPy 2.5.5 wheel | 14.40.33810.0, renamed `msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll` |

Each packaged runtime was matched by SHA-256 to its installation or wheel of
origin. All eleven packaged copies passed Windows Authenticode verification.
Some binaries have the same file version and different hashes. The Microsoft
signature and the presence of a file in an upstream wheel establish
provenance. The applicable redistribution grant must be established separately.

The installed Visual Studio Community 2022 x64 desktop CRT directory under
`VC/Redist/MSVC/14.44.35112` contains all five canonical CRT filenames at file
version 14.44.35211.0. No packaged copy was byte-identical to its counterpart
there. A read-only comparison excluding the PE checksum, security directory
entry and certificate table matched all eight PySide6/Shiboken copies. It
did not match the two CPython 14.51 copies or NumPy's renamed 14.40 copy.
The REDIST list expressly covers unmodified files from the listed directory
for eligible licensees. This comparison identifies a local REDIST equivalent
for Qt/Shiboken. It does not establish a grant for the three unmatched files
or make the bundled copies identical to the local REDIST files.

The included CPython license's Windows-build conditions require downstream
terms protecting Microsoft Distributable Code. The [Visual Studio 2022 REDIST
list](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution)
and [Visual Studio 2026 REDIST list](https://learn.microsoft.com/en-us/visualstudio/releases/2026/redistribution)
describe distribution of listed files in unmodified form under the applicable
Visual Studio terms. The [Community 2022 license](https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/)
permits individuals to use the edition for their own applications. Its
section 4 authorizes distribution of listed code with applications developed
under the license, with significant primary functionality and downstream
agreement to protective terms. Organizational eligibility is subject to
separate conditions. Confirm the publisher's applicable rights and the
acceptance mechanism for **both** the ZIP and installer before publication.
The current archives have notices but no Microsoft-specific acceptance
mechanism.

The official Microsoft runtime end-user terms for
[2015–2022](https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/)
and [v14 2026](https://visualstudio.microsoft.com/license-terms/vs2026-ga-visualcpp-v14-redist-runtime/)
govern use of the runtime. The v14 2026 end-user terms restrict onward
distribution. Resolve the publisher's authority through the applicable
Visual Studio terms and REDIST list instead of relying on an end-user
download or the wheel's license alone.

The least disruptive route is app-local deployment of the x64 desktop CRT
from the installed Community 2022 REDIST directory. CPython 3.14.10 reports
MSVC 1944. The local 14.44.35211.0 CRT exports every runtime symbol directly
or delay-loaded by the candidate, when the NumPy import name is mapped to
`msvcp140.dll`. In a temporary copy, the unchanged official REDIST binaries
replaced the eleven runtime files. The application started and loaded the
local CRT and the hashed-name copy required by NumPy. No release artifact was
modified. This is startup and import-coverage evidence, with installed and
clean-system verification due on the final payload if this route is approved.

An official [Microsoft VC++ x64 Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
can supply the canonical runtime names. The current NumPy extensions
`_multiarray_umath` and `_pocketfft_umath` import
`msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll` directly. Microsoft does
not install that alias. This prerequisite alone would leave an unresolved
import and would not remove the terms for Microsoft code incorporated into
CPython. It adds a separate installation without resolving the key
redistribution question.

**Decision before packaging:** confirm that the publisher can use Community
2022 §4 for this application's distribution and can convey the unchanged,
signed REDIST `msvcp140.dll` under the NumPy import filename. Confirm the
required downstream terms and how they will be accepted for both downloads.
If confirmed, copy the same REDIST files tested above, include the final
notices and source link, and regenerate the ZIP and installer. The existing
application executable can be reused.
