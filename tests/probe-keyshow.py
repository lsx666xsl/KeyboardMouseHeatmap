import ctypes
from ctypes import wintypes
import subprocess

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
res = []


@ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
def cb(hwnd, lparam):
    p2 = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p2))
    ps = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process -Name 'keyboard-mouse-heatmap' -ErrorAction SilentlyContinue).Id"],
        capture_output=True, text=True)
    if p2.value == int(ps.stdout.strip().split()[0]):
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value == "Tauri Window":
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            if r.bottom - r.top > 200:
                res.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
    return True


user32.EnumWindows(cb, 0)
print("keyshow window now:", res)
