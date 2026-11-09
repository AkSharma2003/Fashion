# Install the WearVerse Tally bridge as a Windows service on the Tally cloud server.
# Uses NSSM (https://nssm.cc). Run in an Administrator PowerShell from the tally-bridge folder.
# The service starts with the server and keeps running when users log out (SRS 14.2 step 4).
param(
  [string]$Python = "C:\Python312\python.exe",
  [string]$Nssm = "C:\nssm\nssm.exe"
)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
& $Python -m pip install -r "$here\requirements.txt"
& $Nssm install WearVerseTallyBridge $Python "$here\src\agent.py"
& $Nssm set WearVerseTallyBridge AppDirectory "$here\src"
& $Nssm set WearVerseTallyBridge Start SERVICE_AUTO_START
& $Nssm set WearVerseTallyBridge AppStdout "$here\logs\bridge.log"
& $Nssm set WearVerseTallyBridge AppStderr "$here\logs\bridge.log"
& $Nssm set WearVerseTallyBridge AppRotateFiles 1
New-Item -ItemType Directory -Force -Path "$here\logs" | Out-Null
& $Nssm start WearVerseTallyBridge
Write-Host "Service installed. Log: $here\logs\bridge.log"
