param([string]$Action = "start")
if ($Action -eq "start") {
    $p = Start-Process -FilePath 'F:\TauriProject\KeyboardMouseHeatmap\src-tauri\target\release\keyboard-mouse-heatmap.exe' -PassThru
    Start-Sleep -Seconds 5
    $p.Refresh()
    $alive = -not $p.HasExited
    Write-Output "PID=$($p.Id) Alive=$alive"
    if (-not $alive) { Write-Output "ExitCode=$($p.ExitCode)" }
} elseif ($Action -eq "check") {
    $procs = Get-Process -Name 'keyboard-mouse-heatmap' -ErrorAction SilentlyContinue
    if ($procs) { $procs | ForEach-Object { Write-Output "RUNNING PID=$($_.Id)" } } else { Write-Output "NOT_RUNNING" }
} elseif ($Action -eq "stop") {
    Stop-Process -Name 'keyboard-mouse-heatmap' -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    if (Get-Process -Name 'keyboard-mouse-heatmap' -ErrorAction SilentlyContinue) { Write-Output "STILL_RUNNING" } else { Write-Output "STOPPED" }
}
