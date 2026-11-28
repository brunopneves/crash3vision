#ifndef ReleaseVersion
  #error ReleaseVersion is required. Run scripts/build_installer.py.
#endif
#ifndef BundleDir
  #error BundleDir is required. Run scripts/build_installer.py.
#endif
#ifndef OutputStem
  #define OutputStem "CRASH3Vision-v" + ReleaseVersion + "-Windows-x64-Setup"
#endif

#define BundleExe BundleDir + "\CRASH3Vision.exe"
#if !FileExists(BundleExe)
  #error CRASH3Vision.exe is missing from the portable bundle.
#endif
#if GetFileVersionString(BundleExe) != ReleaseVersion
  #error The executable version does not match app/version.py.
#endif

[Setup]
AppId={{A8169D1C-AD05-48E5-82EB-1B574B797EED}
AppName=CRASH3Vision
AppVersion={#ReleaseVersion}
AppPublisher=Bruno P. Neves
AppPublisherURL=https://github.com/brunopneves/crash3vision
DefaultDirName={userpf}\CRASH3Vision
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
Uninstallable=yes
UninstallDisplayIcon={app}\CRASH3Vision.exe
SetupIconFile=..\app\assets\crash3_icon.ico
VersionInfoCompany=Bruno P. Neves
VersionInfoDescription=CRASH3Vision Windows Setup
VersionInfoProductName=CRASH3Vision
VersionInfoVersion={#ReleaseVersion}.0
VersionInfoTextVersion={#ReleaseVersion}
VersionInfoProductTextVersion={#ReleaseVersion}
OutputDir=..\dist
OutputBaseFilename={#OutputStem}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\windows-installer.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\CRASH3Vision"; Filename: "{app}\CRASH3Vision.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\CRASH3Vision"; Filename: "{app}\CRASH3Vision.exe"; WorkingDir: "{app}"; Tasks: desktopicon
