"""Probe KeyPulse Tauri windows (physical px). Pure ctypes, no subprocess."""
import ctypes
from ctypes import wintypes

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32
user32.SetProcessDPIAware()


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def find_pid(name):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        return None
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    if not kernel32.Process32FirstW(snap, ctypes.byref(entry)):
        return None
    while True:
        if entry.szExeFile.lower() == name.lower():
            return entry.th32ProcessID
        if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
            break
    return None


def list_tauri_windows(pid):
    res = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        p2 = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p2))
        if p2.value == pid:
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls, 256)
            if cls.value == "Tauri Window":
                r = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(r))
                res.append((r.left, r.top, r.right - r.left, r.bottom - r.top,
                            bool(user32.IsWindowVisible(hwnd))))
        return True

    user32.EnumWindows(cb, 0)
    return res


if __name__ == "__main__":
    pid = find_pid("keyboard-mouse-heatmap.exe")
    print("pid:", pid)
    if pid:
        for w in list_tauri_windows(pid):
            print("win:", w)
