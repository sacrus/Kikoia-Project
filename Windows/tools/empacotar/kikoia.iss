; Instalador do Kikoia (Windows). Compilado por construir_windows.ps1, que passa Origem e Saida.

#ifndef Origem
  #error Definir Origem: pasta do executavel (dist\Kikoia)
#endif
#ifndef Saida
  #define Saida "."
#endif

#define NomeApp "Kikoia"
#define Versao "0.1.1"

[Setup]
; Identificador fixo deste produto: nao mudar entre versoes, senao o Windows ve outra aplicacao.
AppId={{ECC8B22B-CBAE-4132-8574-554015001E27}
AppName={#NomeApp}
AppVersion={#Versao}
AppVerName={#NomeApp} {#Versao}
AppPublisher=Luís Patrício
AppPublisherURL=https://www.lplogic.net
AppSupportURL=https://github.com/sacrus/Kikoia-Project
AppUpdatesURL=https://github.com/sacrus/Kikoia-Project/releases
DefaultDirName={autopf}\{#NomeApp}
DefaultGroupName={#NomeApp}
DisableProgramGroupPage=yes
; Instala para o utilizador, sem pedir administrador.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#Saida}
OutputBaseFilename={#NomeApp}-{#Versao}-Windows-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Kikoia.exe
UninstallDisplayName={#NomeApp}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "portugues"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "ingles"; MessagesFile: "compiler:Default.isl"
Name: "espanol"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "frances"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "atalho_ambiente"; Description: "Criar atalho no ambiente de trabalho"; GroupDescription: "Atalhos:"
Name: "firewall"; Description: "Permitir a ligação Wi-Fi do telemóvel na Firewall do Windows (pede autorização de administrador)"; GroupDescription: "Rede:"

[Files]
Source: "{#Origem}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; O AppUserModelID tem de coincidir com o definido pela app (teclado\__main__.py): e isto que faz
; as notificacoes do Windows mostrarem "Kikoia" em vez de "Python".
Name: "{group}\{#NomeApp}"; Filename: "{app}\Kikoia.exe"; AppUserModelID: "Kikoia"
Name: "{autodesktop}\{#NomeApp}"; Filename: "{app}\Kikoia.exe"; AppUserModelID: "Kikoia"; Tasks: atalho_ambiente
Name: "{group}\Desinstalar {#NomeApp}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\Kikoia.exe"; Description: "Abrir o Kikoia"; Flags: nowait postinstall skipifsilent

[Code]
const
  CHAVE_ARRANQUE = 'Software\Microsoft\Windows\CurrentVersion\Run';

procedure CriarRegraFirewall();
var
  ResultCode: Integer;
  Comando: String;
begin
  // Uma so execucao elevada (um pedido de autorizacao): apaga a regra antiga e cria a nova.
  Comando := '/c netsh advfirewall firewall delete rule name="Kikoia" >nul & ' +
             'netsh advfirewall firewall add rule name="Kikoia" dir=in action=allow ' +
             'program="' + ExpandConstant('{app}\Kikoia.exe') + '" enable=yes profile=any';
  if (not ShellExec('runas', 'cmd.exe', Comando, '', SW_HIDE, ewWaitUntilTerminated, ResultCode))
     or (ResultCode <> 0) then
    MsgBox('Não foi possível criar a regra na Firewall. Se o telemóvel não ligar por Wi-Fi, ' +
           'quando o Windows perguntar, permita o Kikoia nas redes privadas e públicas.',
           mbInformation, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('firewall') then
    CriarRegraFirewall();
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // Remove o arranque automatico (o nome atual e o das versoes anteriores).
    RegDeleteValue(HKCU, CHAVE_ARRANQUE, 'Kikoia');
    RegDeleteValue(HKCU, CHAVE_ARRANQUE, 'TecladoRemoto');
  end;
  if CurUninstallStep = usPostUninstall then
  begin
    // Os perfis, teclados e confiancas ficam, salvo se o utilizador pedir para os apagar.
    // Em modo silencioso o Inno responde Sim por defeito, por isso nunca apaga nesse modo.
    if (not UninstallSilent) and
       (MsgBox('Apagar tambem os perfis, teclados e dados guardados do Kikoia?',
               mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES) then
      DelTree(ExpandConstant('{userappdata}\teclado'), True, True, True);
  end;
end;
