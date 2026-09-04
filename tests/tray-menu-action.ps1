param([int]$Downs = 3, [string]$Label = "clear")
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class KS8 {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
    public const uint KEYUP = 0x0002;
    public const uint LEFTDOWN = 0x0002;
    public const uint LEFTUP = 0x0004;
    public const uint RIGHTDOWN = 0x0008;
    public const uint RIGHTUP = 0x0010;
    public static void Tap(byte vk) { keybd_event(vk, 0, 0, UIntPtr.Zero); keybd_event(vk, 0, KEYUP, UIntPtr.Zero); }
}
"@
[KS8]::SetProcessDPIAware() | Out-Null
$root = [System.Windows.Automation.AutomationElement]::RootElement

function Find-Flyout() {
    $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ClassNameProperty, "TopLevelWindowForOverflowXamlIsland")
    return $root.FindAll([System.Windows.Automation.TreeScope]::Children, $cond)
}
function Find-Menu() {
    $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ClassNameProperty, "#32768")
    return $root.FindAll([System.Windows.Automation.TreeScope]::Children, $cond)
}

# 0. If KeyPulse is pinned directly in the taskbar tray area, right-click it there.
function Find-DirectIcon() {
    $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ClassNameProperty, "Shell_TrayWnd")
    $trays = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $cond)
    foreach ($tr in $trays) {
        $kids = $tr.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
        foreach ($k in $kids) {
            if ($k.Current.Name -match "KeyPulse" -and $k.Current.ClassName -eq "SystemTray.NormalButton") {
                $kr = $k.Current.BoundingRectangle
                if ($kr.Width -gt 0 -and $kr.Width -le 100 -and $kr.Y -gt 1500) { return $k }
            }
        }
    }
    return $null
}

# 1. open the flyout if it is not already open
$flyout = $null
$existing = Find-Flyout
if ($existing.Count -gt 0) {
    $flyout = $existing[0]
    Write-Output "flyout already open"
} else {
    [KS8]::SetCursorPos(2933, 2124) | Out-Null
    Start-Sleep -Milliseconds 300
    [KS8]::mouse_event([KS8]::LEFTDOWN,0,0,0,[UIntPtr]::Zero)
    [KS8]::mouse_event([KS8]::LEFTUP,0,0,0,[UIntPtr]::Zero)
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Milliseconds 200
        $f = Find-Flyout
        if ($f.Count -gt 0) { $flyout = $f[0]; break }
    }
}
$directIcon = Find-DirectIcon
if ($directIcon -ne $null) {
    Write-Output "icon found directly in tray"
    $flyout = $null
} else {
    if ($flyout -eq $null) { Write-Output "FAIL: flyout did not open"; exit 1 }
    $fr = $flyout.Current.BoundingRectangle
    Write-Output "flyout open: ($([math]::Round($fr.X)),$([math]::Round($fr.Y)),$([math]::Round($fr.Width)),$([math]::Round($fr.Height)))"
}

# 2. find the KeyPulse icon (in tray directly or inside the flyout)
$icon = $directIcon
if ($icon -eq $null) {
    for ($attempt = 0; $attempt -lt 8 -and $icon -eq $null; $attempt++) {
        $kids = $flyout.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
        foreach ($k in $kids) {
            if ($k.Current.Name -match "KeyPulse") {
                $kr = $k.Current.BoundingRectangle
                if ($kr.Width -gt 0 -and $kr.Width -le 100 -and $kr.Height -gt 0 -and $kr.Height -le 100) {
                    $icon = $k
                    Write-Output "icon candidate: class='$($k.Current.ClassName)' rect=($([math]::Round($kr.X)),$([math]::Round($kr.Y)),$([math]::Round($kr.Width)),$([math]::Round($kr.Height)))"
                    break
                }
            }
        }
        if ($icon -eq $null) { Start-Sleep -Milliseconds 250 }
    }
    if ($icon -eq $null) { Write-Output "FAIL: icon not found"; exit 1 }
}
$ir = $icon.Current.BoundingRectangle
$cx = [int]($ir.X + $ir.Width / 2)
$cy = [int]($ir.Y + $ir.Height / 2)
Write-Output "icon at ($cx,$cy)"

# 4. right-click the icon
Start-Sleep -Milliseconds 300
[KS8]::SetCursorPos($cx, $cy) | Out-Null
Start-Sleep -Milliseconds 250
[KS8]::mouse_event([KS8]::RIGHTDOWN,0,0,0,[UIntPtr]::Zero)
[KS8]::mouse_event([KS8]::RIGHTUP,0,0,0,[UIntPtr]::Zero)

# 5. poll for the native menu
$menu = $null
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Milliseconds 200
    $m = Find-Menu
    if ($m.Count -gt 0) { $menu = $m[0]; break }
}
if ($menu -eq $null) { Write-Output "FAIL: menu did not open"; exit 1 }
$mr = $menu.Current.BoundingRectangle
Write-Output "menu open: ($([math]::Round($mr.X)),$([math]::Round($mr.Y)),$([math]::Round($mr.Width)),$([math]::Round($mr.Height)))"

# 6. navigate: Down x N then Enter
Start-Sleep -Milliseconds 400
for ($i = 0; $i -lt $Downs; $i++) {
    [KS8]::Tap(0x28)
    Start-Sleep -Milliseconds 250
}
[KS8]::Tap(0x0D)
Start-Sleep -Milliseconds 500
Write-Output "OK: menu action '$Label' dispatched"
