Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class KS11 {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
    public const uint KEYUP = 0x0002;
    public const uint RIGHTDOWN = 0x0008;
    public const uint RIGHTUP = 0x0010;
    public static void Tap(byte vk) { keybd_event(vk, 0, 0, UIntPtr.Zero); keybd_event(vk, 0, KEYUP, UIntPtr.Zero); }
}
"@
[KS11]::SetProcessDPIAware() | Out-Null
$root = [System.Windows.Automation.AutomationElement]::RootElement

function Close-Menus() {
    $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ClassNameProperty, "#32768")
    for ($i = 0; $i -lt 3; $i++) {
        $menus = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $cond)
        if ($menus.Count -eq 0) { break }
        [KS11]::Tap(0x1B)  # Esc
        Start-Sleep -Milliseconds 400
    }
    Write-Output "menus closed"
}
function Menu-Open() {
    $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ClassNameProperty, "#32768")
    return ($root.FindAll([System.Windows.Automation.TreeScope]::Children, $cond)).Count -gt 0
}

Close-Menus

# right-click the KeyPulse icon directly in the tray (3053,2088 48x72 -> center 3077,2124)
[KS11]::SetCursorPos(3077, 2124) | Out-Null
Start-Sleep -Milliseconds 300
[KS11]::mouse_event([KS11]::RIGHTDOWN,0,0,0,[UIntPtr]::Zero)
[KS11]::mouse_event([KS11]::RIGHTUP,0,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 900
Write-Output "menu open after right-click: $(Menu-Open)"
for ($i = 0; $i -lt 4; $i++) {
    [KS11]::Tap(0x28)   # Down to quit item
    Start-Sleep -Milliseconds 250
}
[KS11]::Tap(0x0D)
Write-Output "quit dispatched"
