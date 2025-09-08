; Inno Setup Script for Absconditus (Simplified Version)

[Setup]
AppName=Absconditus
AppVersion=1.0
AppPublisher=Aashish Carmel Jai
DefaultDirName={autopf}\Absconditus
DefaultGroupName=Absconditus
OutputBaseFilename=Absconditus-Setup-v1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Absconditus.exe
; This gives your installer itself a custom icon.
SetupIconFile=icon.ico

[Files]
; This points to the .exe you created with PyInstaller.
Source: "dist\Absconditus.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu Shortcut
Name: "{group}\Absconditus"; Filename: "{app}\Absconditus.exe"
; Desktop Shortcut
Name: "{autodesktop}\Absconditus"; Filename: "{app}\Absconditus.exe"; Tasks: desktopicon

[Tasks]
; This creates the "Create a desktop shortcut" checkbox in the installer wizard.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Run]
; This runs your application after the installation is complete.
Filename: "{app}\Absconditus.exe"; Description: "{cm:LaunchProgram,Absconditus}"; Flags: nowait postinstall skipifsilent;