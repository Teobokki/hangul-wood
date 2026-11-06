#define MyVer "1.0.0"
[Setup]
AppId={{B174425E-0736-4E5E-B6DB-85B27CA049D1}
AppName=HANGUL WOOD
AppVersion={#MyVer}
AppVerName=HANGUL WOOD {#MyVer}
AppPublisher=EX Inc./HYPERION DIGITAL
AppPublisherURL=https://github.com/Teobokki/hangul-wood
AppCopyright=©2026 EX Inc./HYPERION DIGITAL ©2026
VersionInfoVersion={#MyVer}.0
VersionInfoCompany=EX Inc.
VersionInfoCopyright=©2026 EX Inc./HYPERION DIGITAL ©2026
VersionInfoProductName=HANGUL WOOD
VersionInfoDescription=HANGUL WOOD Setup
DefaultDirName={localappdata}\Programs\HANGUL WOOD
DefaultGroupName=HANGUL WOOD
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=HANGUL-WOOD-Setup-{#MyVer}
SetupIconFile=assets\logo.ico
UninstallDisplayIcon={app}\HANGUL WOOD.exe
UninstallDisplayName=HANGUL WOOD
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
ChangesAssociations=yes

[Tasks]
Name: "assoc"; Description: "Open .hwd documents with HANGUL WOOD"; GroupDescription: "File types:"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\HANGUL WOOD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
Root: HKCU; Subkey: "Software\Classes\.hwd"; ValueType: string; ValueName: ""; ValueData: "HangulWood.Document"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKCU; Subkey: "Software\Classes\HangulWood.Document"; ValueType: string; ValueName: ""; ValueData: "HANGUL WOOD document"; Flags: uninsdeletekey; Tasks: assoc
Root: HKCU; Subkey: "Software\Classes\HangulWood.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\HANGUL WOOD.exe,0"; Tasks: assoc
Root: HKCU; Subkey: "Software\Classes\HangulWood.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\HANGUL WOOD.exe"" ""%1"""; Tasks: assoc

[Icons]
Name: "{group}\HANGUL WOOD"; Filename: "{app}\HANGUL WOOD.exe"; IconFilename: "{app}\HANGUL WOOD.exe"
Name: "{group}\Uninstall HANGUL WOOD"; Filename: "{uninstallexe}"
Name: "{userdesktop}\HANGUL WOOD"; Filename: "{app}\HANGUL WOOD.exe"; IconFilename: "{app}\HANGUL WOOD.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\HANGUL WOOD.exe"; Description: "Launch HANGUL WOOD now"; Flags: nowait postinstall skipifsilent
