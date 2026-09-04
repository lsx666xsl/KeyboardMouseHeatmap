Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ClassNameProperty, "Tauri Window")
$wins = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $cond)
Write-Output "count=$($wins.Count)"
foreach ($w in $wins) {
    $r = $w.Current.BoundingRectangle
    $rect = "EMPTY"
    if ($r.Width -gt 0 -and $r.Width -lt [double]::MaxValue) {
        $rect = "($([math]::Round($r.X)),$([math]::Round($r.Y)),$([math]::Round($r.Width)),$([math]::Round($r.Height)))"
    }
    Write-Output "name='$($w.Current.Name)' pid=$($w.Current.ProcessId) rect=$rect offscreen=$($w.Current.IsOffscreen)"
}
