#define AppName "Conversation Export Workbench"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef BinaryPath
  #define BinaryPath "..\..\dist\conv-tool.exe"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist"
#endif

[Setup]
AppId={{8E8602D5-8D5B-4AE8-9F1A-7E5A890E5904}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=ngallodev-software
DefaultDirName={localappdata}\Programs\Conversation Export Workbench
DefaultGroupName={#AppName}
OutputDir={#OutputDir}
OutputBaseFilename=ConversationExportWorkbench-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\conv-tool.exe
SetupLogging=yes

[Files]
Source: "{#BinaryPath}"; DestDir: "{app}"; DestName: "conv-tool.exe"; Flags: ignoreversion

[Icons]
Name: "{group}\Conversation Export Workbench"; Filename: "{app}\conv-tool.exe"; Parameters: "format"; WorkingDir: "{userdocs}"
Name: "{group}\Generate Conversation Viewer"; Filename: "{app}\conv-tool.exe"; Parameters: "generate-spa --output output --yes"; WorkingDir: "{userdocs}"
Name: "{group}\Uninstall Conversation Export Workbench"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\conv-tool.exe"; Parameters: "--version"; Flags: runhidden
