param(
    [int]$X, [int]$Y,
    [string]$Button = "left",   # left | right | double
    [int]$Delay = 150
)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class MouseSim3 {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
    public const uint LEFTDOWN = 0x0002;
    public const uint LEFTUP   = 0x0004;
    public const uint RIGHTDOWN = 0x0008;
    public const uint RIGHTUP   = 0x0010;
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X; public int Y; }
}
"@
[MouseSim3]::SetProcessDPIAware() | Out-Null
$ok = [MouseSim3]::SetCursorPos($X, $Y)
Start-Sleep -Milliseconds $Delay
$p = New-Object MouseSim3+POINT
[MouseSim3]::GetCursorPos([ref]$p) | Out-Null
switch ($Button) {
    "left"   { [MouseSim3]::mouse_event([MouseSim3]::LEFTDOWN,0,0,0,[UIntPtr]::Zero); [MouseSim3]::mouse_event([MouseSim3]::LEFTUP,0,0,0,[UIntPtr]::Zero) }
    "double" { [MouseSim3]::mouse_event([MouseSim3]::LEFTDOWN,0,0,0,[UIntPtr]::Zero); [MouseSim3]::mouse_event([MouseSim3]::LEFTUP,0,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 80; [MouseSim3]::mouse_event([MouseSim3]::LEFTDOWN,0,0,0,[UIntPtr]::Zero); [MouseSim3]::mouse_event([MouseSim3]::LEFTUP,0,0,0,[UIntPtr]::Zero) }
    "right"  { [MouseSim3]::mouse_event([MouseSim3]::RIGHTDOWN,0,0,0,[UIntPtr]::Zero); [MouseSim3]::mouse_event([MouseSim3]::RIGHTUP,0,0,0,[UIntPtr]::Zero) }
}
Start-Sleep -Milliseconds 300
Write-Output "CLICKED $Button at ($X,$Y) setOk=$ok cursorNow=($($p.X),$($p.Y))"
