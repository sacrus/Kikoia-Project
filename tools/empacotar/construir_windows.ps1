# Gera o executavel (PyInstaller) e o instalador (Inno Setup) do Kikoia para Windows.
# Uso: powershell -ExecutionPolicy Bypass -File tools\empacotar\construir_windows.ps1
# O instalador fica no ambiente de trabalho; os ficheiros intermedios ficam fora do projeto.

$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$tmp = Join-Path $env:TEMP "opencode\kikoia_build"
$dist = Join-Path $tmp "dist"
$iscc = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
$saida = Join-Path $env:USERPROFILE "Desktop"

if (-not (Test-Path $iscc)) { throw "Inno Setup nao encontrado em $iscc" }

Set-Location $raiz
$env:PYTHONUTF8 = "1"
Remove-Item -Recurse -Force $dist, (Join-Path $tmp "build") -ErrorAction SilentlyContinue

py -m PyInstaller --noconfirm --distpath $dist --workpath (Join-Path $tmp "build") (Join-Path $PSScriptRoot "kikoia.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

# Apagar o instalador anterior: senao o Inno reescreve o mesmo ficheiro e a data de criacao fica a antiga.
Remove-Item -Force (Join-Path $saida "Kikoia-*-Windows-Setup.exe") -ErrorAction SilentlyContinue

& $iscc "/DOrigem=$(Join-Path $dist 'Kikoia')" "/DSaida=$saida" (Join-Path $PSScriptRoot "kikoia.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falhou" }

Write-Output "Instalador: $(Join-Path $saida 'Kikoia-0.1.0-Windows-Setup.exe')"
