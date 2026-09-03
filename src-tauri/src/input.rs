use std::collections::HashSet;
use std::sync::atomic::AtomicBool;
use std::sync::Arc;

#[derive(Clone)]
pub struct RecordingState {
    pub enabled: Arc<AtomicBool>,
}

impl Default for RecordingState {
    fn default() -> Self {
        Self {
            enabled: Arc::new(AtomicBool::new(true)),
        }
    }
}

#[derive(Clone)]
pub struct InputStatus {
    pub available: Arc<AtomicBool>,
}

impl Default for InputStatus {
    fn default() -> Self {
        Self {
            available: Arc::new(AtomicBool::new(false)),
        }
    }
}

#[derive(Default)]
pub struct KeyPressFilter {
    pressed: HashSet<u32>,
}

impl KeyPressFilter {
    pub fn accept_down(&mut self, physical_code: u32) -> bool {
        self.pressed.insert(physical_code)
    }

    pub fn accept_up(&mut self, physical_code: u32) {
        self.pressed.remove(&physical_code);
    }
}

#[cfg(windows)]
mod windows_listener {
    use super::{KeyPressFilter, RecordingState};
    use crate::storage::StatsStore;
    use std::sync::atomic::Ordering;
    use std::sync::mpsc::{self, Receiver, Sender, SyncSender};
    use std::sync::{Arc, Mutex, OnceLock};
    use std::thread::{self, JoinHandle};
    use std::time::{Duration, Instant};
    use tauri::{AppHandle, Emitter};
    use windows::Win32::Foundation::{HINSTANCE, LPARAM, LRESULT, WPARAM};
    use windows::Win32::System::LibraryLoader::GetModuleHandleW;
    use windows::Win32::System::Threading::GetCurrentThreadId;
    use windows::Win32::UI::WindowsAndMessaging::{
        CallNextHookEx, DispatchMessageW, GetMessageW, PeekMessageW, PostThreadMessageW,
        SetWindowsHookExW, TranslateMessage, UnhookWindowsHookEx, HC_ACTION, KBDLLHOOKSTRUCT, MSG,
        MSLLHOOKSTRUCT, PM_NOREMOVE, WH_KEYBOARD_LL, WH_MOUSE_LL, WM_APP, WM_KEYDOWN, WM_KEYUP,
        WM_LBUTTONDOWN, WM_MBUTTONDOWN, WM_MOUSEHWHEEL, WM_MOUSEWHEEL, WM_QUIT, WM_RBUTTONDOWN,
        WM_SYSKEYDOWN, WM_SYSKEYUP, WM_XBUTTONDOWN,
    };

    const LLKHF_INJECTED_FLAG: u32 = 0x0000_0010;
    const KEYBOARD_WAKE_MESSAGE: u32 = WM_APP + 1;

    #[derive(Debug)]
    enum NativeInput {
        KeyDown {
            physical_code: u32,
            key_id: String,
            label: String,
        },
        KeyUp {
            physical_code: u32,
        },
        Mouse {
            action_id: String,
            label: String,
        },
    }

    static INPUT_SENDER: OnceLock<Mutex<Option<Sender<NativeInput>>>> = OnceLock::new();

    pub struct InputListener {
        hook_thread_id: u32,
        _processor: Option<JoinHandle<()>>,
    }

    impl InputListener {
        pub fn start(
            app: AppHandle,
            store: Arc<StatsStore>,
            recording: RecordingState,
        ) -> Result<Self, String> {
            let (event_tx, event_rx) = mpsc::channel();
            let (ready_tx, ready_rx) = mpsc::sync_channel(1);
            let hook_thread = thread::Builder::new()
                .name("keypulse-input-hooks".to_string())
                .spawn(move || hook_thread_main(event_tx, ready_tx))
                .map_err(|error| error.to_string())?;

            let hook_thread_id = ready_rx
                .recv_timeout(Duration::from_secs(3))
                .map_err(|error| format!("input hook startup timed out: {error}"))??;

            let processor = thread::Builder::new()
                .name("keypulse-input-aggregator".to_string())
                .spawn(move || process_events(app, store, recording, event_rx))
                .map_err(|error| error.to_string())?;

            // The hook thread owns the Windows message loop. It will exit after WM_QUIT;
            // the JoinHandle is intentionally detached because the UI may close on the
            // same thread that is dropping Tauri managed state.
            drop(hook_thread);

            Ok(Self {
                hook_thread_id,
                _processor: Some(processor),
            })
        }
    }

    impl Drop for InputListener {
        fn drop(&mut self) {
            unsafe {
                let _ = PostThreadMessageW(self.hook_thread_id, WM_QUIT, WPARAM(0), LPARAM(0));
            }
        }
    }

    fn hook_thread_main(sender: Sender<NativeInput>, ready: SyncSender<Result<u32, String>>) {
        let thread_id = unsafe { GetCurrentThreadId() };
        let mut bootstrap_message = MSG::default();
        unsafe {
            // A message queue is created lazily by Windows. PeekMessage makes it safe for
            // the owner thread to receive WM_QUIT immediately after startup.
            let _ = PeekMessageW(&mut bootstrap_message, None, 0, 0, PM_NOREMOVE);
        }

        let slot = INPUT_SENDER.get_or_init(|| Mutex::new(None));
        if let Ok(mut current_sender) = slot.lock() {
            *current_sender = Some(sender);
        } else {
            let _ = ready.send(Err("input sender lock is poisoned".to_string()));
            return;
        }

        let module = match unsafe { GetModuleHandleW(None) } {
            Ok(module) => module,
            Err(error) => {
                clear_sender();
                let _ = ready.send(Err(format!("GetModuleHandleW failed: {error}")));
                return;
            }
        };

        let keyboard_hook = match unsafe {
            SetWindowsHookExW(
                WH_KEYBOARD_LL,
                Some(keyboard_proc),
                Some(HINSTANCE(module.0)),
                0,
            )
        } {
            Ok(hook) => hook,
            Err(error) => {
                clear_sender();
                let _ = ready.send(Err(format!("keyboard hook failed: {error}")));
                return;
            }
        };

        let mouse_hook = match unsafe {
            SetWindowsHookExW(WH_MOUSE_LL, Some(mouse_proc), Some(HINSTANCE(module.0)), 0)
        } {
            Ok(hook) => hook,
            Err(error) => {
                unsafe {
                    let _ = UnhookWindowsHookEx(keyboard_hook);
                }
                clear_sender();
                let _ = ready.send(Err(format!("mouse hook failed: {error}")));
                return;
            }
        };

        let _ = ready.send(Ok(thread_id));
        let mut message = MSG::default();
        loop {
            let result = unsafe { GetMessageW(&mut message, None, 0, 0) };
            if result.0 > 0 {
                if message.message == KEYBOARD_WAKE_MESSAGE {
                    continue;
                }
                unsafe {
                    let _ = TranslateMessage(&message);
                    DispatchMessageW(&message);
                }
            } else {
                break;
            }
        }

        unsafe {
            let _ = UnhookWindowsHookEx(keyboard_hook);
            let _ = UnhookWindowsHookEx(mouse_hook);
        }
        clear_sender();
    }

    fn process_events(
        app: AppHandle,
        store: Arc<StatsStore>,
        recording: RecordingState,
        receiver: Receiver<NativeInput>,
    ) {
        let mut filter = KeyPressFilter::default();
        let mut dirty = false;
        let mut last_emit = Instant::now();

        loop {
            match receiver.recv_timeout(Duration::from_millis(250)) {
                Ok(event) => {
                    let recorded = match event {
                        NativeInput::KeyDown {
                            physical_code,
                            key_id,
                            label,
                        } => {
                            let is_new_press = filter.accept_down(physical_code);
                            if is_new_press && recording.enabled.load(Ordering::Relaxed) {
                                store.record_key(&key_id, &label).is_ok()
                            } else {
                                false
                            }
                        }
                        NativeInput::KeyUp { physical_code } => {
                            filter.accept_up(physical_code);
                            false
                        }
                        NativeInput::Mouse { action_id, label } => {
                            recording.enabled.load(Ordering::Relaxed)
                                && store.record_mouse(&action_id, &label).is_ok()
                        }
                    };
                    dirty |= recorded;
                }
                Err(mpsc::RecvTimeoutError::Timeout) => {}
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
            }

            if dirty && last_emit.elapsed() >= Duration::from_millis(350) {
                emit_snapshot(&app, &store);
                dirty = false;
                last_emit = Instant::now();
            }
        }

        if dirty {
            emit_snapshot(&app, &store);
        }
    }

    fn emit_snapshot(app: &AppHandle, store: &StatsStore) {
        if let Ok(snapshot) = store.dashboard_today() {
            let _ = app.emit("stats-updated", snapshot);
        }
    }

    fn clear_sender() {
        if let Some(slot) = INPUT_SENDER.get() {
            if let Ok(mut sender) = slot.lock() {
                *sender = None;
            }
        }
    }

    fn send_input(event: NativeInput) {
        if let Some(slot) = INPUT_SENDER.get() {
            if let Ok(sender) = slot.lock() {
                if let Some(sender) = sender.as_ref() {
                    let _ = sender.send(event);
                }
            }
        }
    }

    unsafe extern "system" fn keyboard_proc(code: i32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
        if code == HC_ACTION as i32 && lparam.0 != 0 {
            let data = &*(lparam.0 as *const KBDLLHOOKSTRUCT);
            let flags = data.flags.0;
            if flags & LLKHF_INJECTED_FLAG == 0 {
                let message = wparam.0 as u32;
                let physical_code = (data.scanCode << 1) | (flags & 0x01);
                if matches!(message, WM_KEYDOWN | WM_SYSKEYDOWN) {
                    if let Some((key_id, label)) = key_descriptor(data.vkCode, data.scanCode, flags)
                    {
                        send_input(NativeInput::KeyDown {
                            physical_code,
                            key_id,
                            label,
                        });
                    }
                } else if matches!(message, WM_KEYUP | WM_SYSKEYUP) {
                    send_input(NativeInput::KeyUp { physical_code });
                }
            }
        }

        CallNextHookEx(None, code, wparam, lparam)
    }

    unsafe extern "system" fn mouse_proc(code: i32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
        if code == HC_ACTION as i32 && lparam.0 != 0 {
            let data = &*(lparam.0 as *const MSLLHOOKSTRUCT);
            match wparam.0 as u32 {
                WM_LBUTTONDOWN => send_input(NativeInput::Mouse {
                    action_id: "left-click".into(),
                    label: "左键".into(),
                }),
                WM_RBUTTONDOWN => send_input(NativeInput::Mouse {
                    action_id: "right-click".into(),
                    label: "右键".into(),
                }),
                WM_MBUTTONDOWN => send_input(NativeInput::Mouse {
                    action_id: "middle-click".into(),
                    label: "中键".into(),
                }),
                WM_XBUTTONDOWN => {
                    let button = ((data.mouseData >> 16) & 0xffff) as u16;
                    let suffix = if button == 1 { "1" } else { "2" };
                    send_input(NativeInput::Mouse {
                        action_id: format!("x-button-{suffix}"),
                        label: format!("侧键{suffix}"),
                    });
                }
                WM_MOUSEWHEEL => {
                    let delta = (data.mouseData >> 16) as i16;
                    let (action_id, label) = if delta > 0 {
                        ("wheel-up", "滚轮向上")
                    } else {
                        ("wheel-down", "滚轮向下")
                    };
                    send_input(NativeInput::Mouse {
                        action_id: action_id.into(),
                        label: label.into(),
                    });
                }
                WM_MOUSEHWHEEL => {
                    let delta = (data.mouseData >> 16) as i16;
                    let (action_id, label) = if delta > 0 {
                        ("wheel-right", "水平滚轮向右")
                    } else {
                        ("wheel-left", "水平滚轮向左")
                    };
                    send_input(NativeInput::Mouse {
                        action_id: action_id.into(),
                        label: label.into(),
                    });
                }
                _ => {}
            }
        }

        CallNextHookEx(None, code, wparam, lparam)
    }

    fn key_descriptor(vk: u32, scan_code: u32, flags: u32) -> Option<(String, String)> {
        let descriptor = match vk {
            0x08 => ("backspace", "Backspace"),
            0x09 => ("tab", "Tab"),
            0x0D => ("enter", "Enter"),
            0x10 | 0xA0 => {
                if scan_code == 0x36 {
                    ("shift-right", "Shift")
                } else {
                    ("shift-left", "Shift")
                }
            }
            0x11 | 0xA2 => {
                if flags & 0x01 != 0 {
                    ("ctrl-right", "Ctrl")
                } else {
                    ("ctrl-left", "Ctrl")
                }
            }
            0x12 | 0xA4 => {
                if flags & 0x01 != 0 {
                    ("alt-right", "Alt")
                } else {
                    ("alt-left", "Alt")
                }
            }
            0x1B => ("escape", "Esc"),
            0x20 => ("space", "Space"),
            0x21 => ("page-up", "PageUp"),
            0x22 => ("page-down", "PageDown"),
            0x23 => ("end", "End"),
            0x24 => ("home", "Home"),
            0x25 => ("arrow-left", "←"),
            0x26 => ("arrow-up", "↑"),
            0x27 => ("arrow-right", "→"),
            0x28 => ("arrow-down", "↓"),
            0x2D => ("insert", "Insert"),
            0x2E => ("delete", "Delete"),
            0x30..=0x39 => {
                let label = char::from_u32(vk).unwrap_or('?').to_string();
                return Some((label.to_lowercase(), label));
            }
            0x41..=0x5A => {
                let label = char::from_u32(vk).unwrap_or('?').to_string();
                return Some((label.to_lowercase(), label));
            }
            0x5B => ("win-left", "Win"),
            0x5C => ("win-right", "Win"),
            0x70..=0x7B => {
                let label = format!("F{}", vk - 0x6F);
                return Some((label.to_lowercase(), label));
            }
            0x90 => ("num-lock", "NumLock"),
            0x91 => ("scroll-lock", "ScrollLock"),
            0xBA => ("semicolon", ";"),
            0xBB => ("equal", "="),
            0xBC => ("comma", ","),
            0xBD => ("minus", "-"),
            0xBE => ("period", "."),
            0xBF => ("slash", "/"),
            0xC0 => ("backquote", "~"),
            0xDB => ("bracket-left", "["),
            0xDC => ("backslash", "\\"),
            0xDD => ("bracket-right", "]"),
            0xDE => ("quote", "'"),
            _ => return None,
        };
        Some((descriptor.0.to_string(), descriptor.1.to_string()))
    }
}

#[cfg(windows)]
pub use windows_listener::InputListener;

#[cfg(not(windows))]
pub struct InputListener;

#[cfg(not(windows))]
impl InputListener {
    pub fn start(
        _app: tauri::AppHandle,
        _store: std::sync::Arc<crate::storage::StatsStore>,
        _recording: RecordingState,
    ) -> Result<Self, String> {
        Err("global input listener is currently supported on Windows only".to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::{InputStatus, KeyPressFilter};
    use std::sync::atomic::Ordering;

    #[test]
    fn filters_auto_repeat_until_key_up() {
        let mut filter = KeyPressFilter::default();
        assert!(filter.accept_down(30));
        assert!(!filter.accept_down(30));
        filter.accept_up(30);
        assert!(filter.accept_down(30));
    }

    #[test]
    fn tracks_different_physical_keys_independently() {
        let mut filter = KeyPressFilter::default();
        assert!(filter.accept_down(30));
        assert!(filter.accept_down(31));
        assert!(!filter.accept_down(30));
        filter.accept_up(30);
        assert!(filter.accept_down(30));
    }

    #[test]
    fn input_status_starts_unavailable_until_hook_is_ready() {
        let status = InputStatus::default();
        assert!(!status.available.load(Ordering::Relaxed));
        status.available.store(true, Ordering::Relaxed);
        assert!(status.available.load(Ordering::Relaxed));
    }
}
