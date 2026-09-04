param([string]$Msi = "F:\TauriProject\KeyboardMouseHeatmap\src-tauri\target\release\bundle\msi\Keyboard Mouse Heatmap_0.1.0_x64_en-US.msi")
$log = "$env:TEMP\kp-msi-install.log"
$proc = Start-Process msiexec.exe -ArgumentList @("/i", "`"$Msi`"", "/qn", "/norestart", "/l*v", "`"$log`"") -PassThru -Wait
Write-Output "msiexec exit=$($proc.ExitCode)"
# check whether the app got installed
$installed = Test-Path "$env:ProgramFiles\Keyboard Mouse Heatmap\keyboard-mouse-heatmap.exe"
$installedX86 = Test-Path "${env:ProgramFiles(x86)}\Keyboard Mouse Heatmap\keyboard-mouse-heatmap.exe"
$local = Test-Path "$env:LOCALAPPDATA\Programs\Keyboard Mouse Heatmap\keyboard-mouse-heatmap.exe"
Write-Output "installed x64: $installed, x86: $installedX86, local: $local"
Get-Content $log -Tail 6 -ErrorAction SilentlyContinue | ForEach-Object { Write-Output "log: $_" }
