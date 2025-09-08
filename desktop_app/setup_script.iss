; Inno Setup Script for Absconditus (Two-Part Application)

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
; The icon shown in "Add/Remove Programs" should be for the main GUI.
UninstallDisplayIcon={app}\Absconditus_GUI.exe
; This gives the installer itself a custom icon.
SetupIconFile=icon.ico

[Files]
; We now install TWO separate executables that you will create with PyInstaller.
; 1. The background service (built from background_service.py)
;    This is the core engine with the API and tray icon.
Source: "dist\Absconditus_Service.exe"; DestDir: "{app}"; Flags: ignoreversion

; 2. The GUI client (built from gui_client.py)
;    This is the on-demand window the user opens to see their vault.
Source: "dist\Absconditus_GUI.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; The main Start Menu shortcut points to the on-demand GUI client.
Name: "{group}\Absconditus"; Filename: "{app}\Absconditus_GUI.exe"

; The optional Desktop shortcut also points to the GUI client.
Name: "{autodesktop}\Absconditus"; Filename: "{app}\Absconditus_GUI.exe"; Tasks: desktopicon

; *** THIS IS THE MOST CRITICAL NEW PART ***
; This entry places a shortcut to the background service into the
; Windows Startup folder. This ensures the service runs automatically
; every time the user logs in.
Name: "{commonstartup}\Absconditus Service"; Filename: "{app}\Absconditus_Service.exe"

[Tasks]
; This creates the "Create a desktop shortcut" checkbox in the installer wizard.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Run]
; After installation completes, we launch the background service first to ensure it's running.
; The 'postinstall' flag ensures it runs after all files are copied.
Filename: "{app}\Absconditus_Service.exe"; Description: "Launch background service"; Flags: nowait postinstall skipifsilent

; Then, we can optionally launch the main GUI window for the user.
Filename: "{app}\Absconditus_GUI.exe"; Description: "{cm:LaunchProgram,Absconditus}"; Flags: nowait postinstall skipifsilent