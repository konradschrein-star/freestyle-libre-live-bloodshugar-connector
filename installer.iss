; Inno Setup Script for FreeStyle Libre 3 Monitor
; Generates a professional Windows Setup Wizard (FreeStyleLibre_Setup.exe)

#define MyAppName "FreeStyle Libre 3 Monitor"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "Konrad Schreiner"
#define MyAppURL "https://github.com/konradschrein-star/freestyle-libre-live-bloodshugar-connector"
#define MyAppExeName "FreeStyleLibreMonitor.exe"

[Setup]
AppId={{B42E7599-563C-4D2A-9491-036B54247891}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\FreeStyleLibreMonitor
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=FreeStyleLibre_Setup
SetupIconFile=assets\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Beim Windows-Start automatisch im Hintergrund ausführen"; GroupDescription: "Autostart:"

[Files]
Source: "dist\FreeStyleLibreTaskbar.exe"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion
Source: "assets\app_icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: autostart

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FreeStyleLibreMonitor"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{localappdata}\FreeStyleLibreTaskbar\app.log"
