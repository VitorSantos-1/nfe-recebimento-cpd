; ============================================================================
; Instalador Inno Setup 7 - Formulario CPD (Recebimentos) - Desktop Nativo
; Gera: dist_installer\Formulario_CPD_Setup_v3.1.exe
;
; ATUALIZACAO NO LUGAR da v2.7: usa o MESMO AppId e o MESMO local de instalacao
; da versao 2.7 (por usuario, em AppData\Local\Programs\Formulario_CPD). Ao rodar,
; o Inno detecta a instalacao existente e a atualiza (substitui o .exe), mantendo
; o config.json que ja estiver la.
;
; Como compilar:
;   1) python build_desktop.py           (gera o Formulario_CPD.exe nativo)
;   2) copiar Formulario_CPD.exe para ESTA pasta (ao lado deste .iss)
;   3) "C:\Program Files\Inno Setup 7\ISCC.exe" installer_cpd.iss
;
; Para uma proxima versao: mude apenas AppVersion e OutputBaseFilename e
; MANTENHA o AppId abaixo.
; ============================================================================

#define MyAppName "Formulario CPD Recebimentos"
#define MyAppVersion "3.1"
#define MyAppExe "Formulario_CPD.exe"
#define MyAppPublisher "Supermercados Opcao"

[Setup]
; AppId igual ao da v2.7 instalada -> atualiza no lugar (NAO mude este GUID).
AppId={{8F5B1E9A-C1A2-4D0E-8E5F-7E8B9A0C1D2E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; {autopf} + lowest = AppData\Local\Programs (mesmo lugar da v2.7)
DefaultDirName={autopf}\Formulario_CPD
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist_installer
OutputBaseFilename=Formulario_CPD_Setup_v3.1
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
; Nao usa Restart Manager (evita travas). Feche o programa antes de atualizar.
CloseApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#MyAppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
; config.json: instala so se ainda nao existir, para nao apagar a config do cliente
Source: "config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
