param(
    [string]$Keys = ""   # e.g. "enter", "down", "up", "apps", "esc", "right", "left", "space", "tab", "f10"
)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class KeySim {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
    public const uint KEYUP = 0x0002;
    public static void Tap(byte vk) { keybd_event(vk, 0, 0, UIntPtr.Zero); keybd_event(vk, 0, KEYUP, UIntPtr.Zero); }
    public static void WinTap(byte vk) {
        keybd_event(0x5B, 0, 0, UIntPtr.Zero);  // LWIN down
        keybd_event(vk, 0, 0, UIntPtr.Zero);
        keybd_event(vk, 0, KEYUP, UIntPtr.Zero);
        keybd_event(0x5B, 0, KEYUP, UIntPtr.Zero);
    }
}
"@
[KeySim]::SetProcessDPIAware() | Out-Null
$map = @{
    "enter" = 0x0D; "esc" = 0x1B; "space" = 0x20; "tab" = 0x09;
    "up" = 0x26; "down" = 0x28; "left" = 0x25; "right" = 0x27;
    "apps" = 0x5D; "f10" = 0x79; "shift" = 0x10; "ctrl" = 0x11; "alt" = 0x12;
}
foreach ($k in $Keys.Split(",") | Where-Object { $_ }) {
    if ($k -eq "winb") { [KeySim]::WinTap(0x42) }
    elseif ($map.ContainsKey($k)) { [KeySim]::Tap($map[$k]) }
    else { Write-Output "UNKNOWN key $k"; exit 2 }
    Start-Sleep -Milliseconds 250
}
Write-Output "KEYS $Keys sent"
