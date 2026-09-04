$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9222'
$p = Start-Process -FilePath 'F:\TauriProject\KeyboardMouseHeatmap\src-tauri\target\release\keyboard-mouse-heatmap.exe' -PassThru
Start-Sleep -Seconds 6
$p.Refresh()
$alive = -not $p.HasExited
Write-Output "PID=$($p.Id) Alive=$alive"
try {
    $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:9222/json/version' -UseBasicParsing -TimeoutSec 5
    Write-Output "CDP_OK $($resp.StatusCode)"
} catch {
    Write-Output "CDP_FAIL $($_.Exception.Message)"
}
