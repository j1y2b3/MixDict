#include "dist/config.iss"

#define AppPublisher "Jin Yubin"
#define AppURL "https://github.com/j1y2b3/MixDict"

[Setup]
AppId={{32E3A4CD-D5EA-425E-88BD-00905E8D0491}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

AppMutex={#AppName}AppMutex
CloseApplications=yes
RestartApplications=no

DefaultGroupName={#AppDisplayName}
AllowNoIcons=yes

DefaultDirName={autopf}\{#AppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

SetupMutex={#AppName}SetupMutex
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}

OutputDir=dist
OutputBaseFilename={#OutputBaseFilename}

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SolidCompression=yes

WizardStyle=modern dynamic

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\MixDict\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppDisplayName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#AppDisplayName}}"; Filename: "{#AppURL}"
Name: "{group}\{cm:UninstallProgram,{#AppDisplayName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppDisplayName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; For uninstall delete.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "{#AppName}"; Flags: uninsdeletevalue dontcreatekey
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"; ValueType: none; ValueName: "{#AppName}"; Flags: uninsdeletevalue dontcreatekey

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
{ Aissited by DeepSeek, since I'm not familiar with Pascal. }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
  Elapsed: Integer;
  mres: Integer;
begin
  case CurUninstallStep of
    usAppMutexCheck:
      begin
        { Ask the running instance to exit, then wait until it has actually
          released its mutex before Uninstall performs its own AppMutex check.
          Doing this here (instead of in InitializeUninstall) keeps the app
          alive if the user cancels the "confirm uninstall" prompt. }
        if Exec(ExpandConstant('{app}\{#AppExeName}'), '--quit', '',
                SW_HIDE, ewWaitUntilTerminated, ResultCode) then begin
          Elapsed := 0;
          while CheckForMutexes('{#AppName}AppMutex') and (Elapsed < 15000) do begin
            Sleep(200);
            Elapsed := Elapsed + 200;
          end;
        end;
      end;

    { Adapted from https://stackoverflow.com/questions/4828674/how-to-clear-users-app-data-folders-with-inno-setup }
    usPostUninstall:
      begin
        { Silent uninstall must not block on a prompt, so keep user data. }
        if UninstallSilent then
          Exit;

        mres := MsgBox('是否同时删除 “{#AppDisplayName}” 的用户数据？（包含用户词典源）'
                       ,mbConfirmation, MB_YESNO or MB_DEFBUTTON2);
        if mres = IDYES then
          DelTree(ExpandConstant('{localappdata}\{#AppName}'), True, True, True);
      end;
  end;
end;