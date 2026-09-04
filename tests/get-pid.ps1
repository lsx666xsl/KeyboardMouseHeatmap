$p = Get-Process -Name 'keyboard-mouse-heatmap' -ErrorAction SilentlyContinue
if ($p) { Write-Output $p.Id } else { Write-Output 'NONE' }
