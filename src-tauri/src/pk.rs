//! LAN typing duel: discover peers over UDP broadcast, challenge over TCP,
//! then each side reports its own local key-press counter while the server
//! drives a 60-second countdown relayed as ticks. Scores live in the frontend
//! (it counts the same keyshow-event stream that drives sounds); Rust relays
//! counts, ticks and the end signal.

use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader, Write};
use std::net::{SocketAddr, TcpListener, TcpStream, UdpSocket};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager};

pub const PK_UDP_PORT: u16 = 46666;
const PK_DURATION_SECS: u64 = 60;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct HelloMsg {
    t: String,
    name: String,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PeerInfo {
    pub name: String,
    pub host: String,
    pub port: u16,
}

#[derive(Default)]
pub struct PkState {
    pub active: AtomicBool,
    pub peers: Mutex<Vec<PeerInfo>>,
    /// Active duel writer used to relay our local counter to the peer.
    pub writer: Mutex<Option<TcpStream>>,
}

fn send_line(stream: &mut TcpStream, text: &str) {
    let _ = writeln!(stream, "{text}");
    let _ = stream.flush();
}

fn relay_loop(mut reader: BufReader<TcpStream>, app: AppHandle) {
    loop {
        let mut line = String::new();
        match reader.read_line(&mut line) {
            Ok(0) | Err(_) => break,
            Ok(_) => {
                if let Ok(msg) = serde_json::from_str::<serde_json::Value>(&line) {
                    let kind = msg.get("t").and_then(|v| v.as_str()).unwrap_or("");
                    match kind {
                        "count" => {
                            if let Some(v) = msg.get("v").and_then(|x| x.as_u64()) {
                                let _ = app.emit(
                                    "pk-event",
                                    serde_json::json!({ "type": "peerCount", "value": v }),
                                );
                            }
                        }
                        "tick" => {
                            if let Some(left) = msg.get("left").and_then(|x| x.as_u64()) {
                                let _ = app.emit(
                                    "pk-event",
                                    serde_json::json!({ "type": "tick", "left": left }),
                                );
                            }
                        }
                        "end" => {
                            let _ = app.emit("pk-event", serde_json::json!({ "type": "ended" }));
                            break;
                        }
                        _ => {}
                    }
                }
            }
        }
    }
    app.state::<PkState>().active.store(false, Ordering::SeqCst);
}

fn server_timer(mut writer: TcpStream, app: AppHandle) {
    let started = std::time::Instant::now();
    loop {
        let left = PK_DURATION_SECS.saturating_sub(started.elapsed().as_secs());
        send_line(&mut writer, &format!("{{\"t\":\"tick\",\"left\":{left}}}"));
        let _ = app.emit("pk-event", serde_json::json!({ "type": "tick", "left": left }));
        if left == 0 {
            send_line(&mut writer, "{\"t\":\"end\"}");
            let _ = app.emit("pk-event", serde_json::json!({ "type": "ended" }));
            break;
        }
        thread::sleep(Duration::from_secs(1));
    }
}

/// Start advertising + listening. Returns the TCP port others can challenge.
pub fn start_host(app: &AppHandle, name: String) -> Result<u16, String> {
    let state = app.state::<PkState>();
    if state.active.swap(true, Ordering::SeqCst) {
        return Err("PK 已在运行中".into());
    }

    let listener = TcpListener::bind("0.0.0.0:0").map_err(|e| e.to_string())?;
    let port = listener.local_addr().map_err(|e| e.to_string())?.port();

    let adv_socket = UdpSocket::bind("0.0.0.0:0").map_err(|e| e.to_string())?;
    adv_socket.set_broadcast(true).map_err(|e| e.to_string())?;
    let adv_app = app.clone();
    let adv_name = name.clone();
    let adv_port = port;
    thread::spawn(move || {
        let payload = serde_json::json!({ "t": "kp-pk-adv", "name": adv_name, "port": adv_port });
        while adv_app.state::<PkState>().active.load(Ordering::SeqCst) {
            let _ = adv_socket.send_to(
                payload.to_string().as_bytes(),
                format!("255.255.255.255:{PK_UDP_PORT}"),
            );
            thread::sleep(Duration::from_millis(1800));
        }
    });

    let listen_socket =
        UdpSocket::bind(format!("0.0.0.0:{PK_UDP_PORT}")).map_err(|e| e.to_string())?;
    let disc_app = app.clone();
    thread::spawn(move || {
        let mut buf = [0u8; 1024];
        while let Ok((len, from)) = listen_socket.recv_from(&mut buf) {
            if let Ok(text) = std::str::from_utf8(&buf[..len]) {
                if let Ok(msg) = serde_json::from_str::<serde_json::Value>(text) {
                    if msg.get("t").and_then(|v| v.as_str()) == Some("kp-pk-adv") {
                        if let (Some(pname), Some(pport)) = (
                            msg.get("name").and_then(|v| v.as_str()),
                            msg.get("port").and_then(|v| v.as_u64()),
                        ) {
                            if let Ok(mut peers) = disc_app.state::<PkState>().peers.lock() {
                                let host = from.ip().to_string();
                                peers.retain(|p| !(p.host == host && p.port == pport as u16));
                                peers.push(PeerInfo {
                                    name: pname.to_string(),
                                    host,
                                    port: pport as u16,
                                });
                            }
                        }
                    }
                }
            }
        }
    });

    let accept_app = app.clone();
    thread::spawn(move || {
        for stream in listener.incoming() {
            let Ok(stream) = stream else { continue };
            let Ok(reader_stream) = stream.try_clone() else { continue };
            let Ok(writer_a) = stream.try_clone() else { continue };
            let Ok(writer_b) = stream.try_clone() else { continue };
            if let Ok(mut writer_slot) = accept_app.state::<PkState>().writer.lock() {
                *writer_slot = Some(writer_a);
            }
            let reader = BufReader::new(reader_stream);
            let _ = accept_app.emit(
                "pk-event",
                serde_json::json!({ "type": "started", "role": "server", "seconds": PK_DURATION_SECS }),
            );
            let app_r = accept_app.clone();
            thread::spawn(move || relay_loop(reader, app_r));
            thread::spawn(move || server_timer(writer_b, accept_app));
            break; // one duel at a time
        }
    });

    let _ = app.emit(
        "pk-event",
        serde_json::json!({ "type": "hosting", "port": port, "name": name }),
    );
    Ok(port)
}

/// Connect to a host and open the duel as the client.
pub fn start_client(app: &AppHandle, name: String, host: String, port: u16) -> Result<(), String> {
    let state = app.state::<PkState>();
    if state.active.swap(true, Ordering::SeqCst) {
        return Err("PK 已在运行中".into());
    }
    let addr: SocketAddr = format!("{host}:{port}")
        .parse::<SocketAddr>()
        .map_err(|e| e.to_string())?;
    let mut stream = TcpStream::connect(addr).map_err(|e| e.to_string())?;
    send_line(
        &mut stream,
        &serde_json::json!({ "t": "hello", "name": name }).to_string(),
    );
    if let Ok(mut writer_slot) = app.state::<PkState>().writer.lock() {
        *writer_slot = Some(stream.try_clone().map_err(|e| e.to_string())?);
    }
    let Ok(reader_stream) = stream.try_clone() else {
        return Err("无法建立会话".into());
    };
    let reader = BufReader::new(reader_stream);
    let app_r = app.clone();
    thread::spawn(move || relay_loop(reader, app_r));
    let _ = app.emit(
        "pk-event",
        serde_json::json!({ "type": "started", "role": "client", "seconds": PK_DURATION_SECS }),
    );
    Ok(())
}

#[tauri::command]
pub fn pk_start(app: AppHandle, name: String) -> Result<u16, String> {
    start_host(&app, name)
}

#[tauri::command]
pub fn pk_challenge(app: AppHandle, name: String, host: String, port: u16) -> Result<(), String> {
    start_client(&app, name, host, port)
}

#[tauri::command]
pub fn pk_report(app: AppHandle, value: u64) -> Result<(), String> {
    let _ = app.emit("pk-event", serde_json::json!({ "type": "selfCount", "value": value }));
    let writer = app
        .state::<PkState>()
        .writer
        .lock()
        .map_err(|_| "pk writer poisoned".to_string())?
        .as_mut()
        .map(|s| s.try_clone())
        .transpose()
        .map_err(|e| e.to_string())?;
    if let Some(mut stream) = writer {
        let _ = writeln!(stream, "{{\"t\":\"count\",\"v\":{value}}}");
        let _ = stream.flush();
    }
    Ok(())
}

#[tauri::command]
pub fn pk_stop(app: AppHandle) -> Result<(), String> {
    app.state::<PkState>().active.store(false, Ordering::SeqCst);
    if let Ok(mut writer) = app.state::<PkState>().writer.lock() {
        *writer = None;
    }
    let _ = app.emit("pk-event", serde_json::json!({ "type": "stopped" }));
    Ok(())
}

#[tauri::command]
pub fn pk_peers(app: AppHandle) -> Result<Vec<PeerInfo>, String> {
    let state = app.state::<PkState>();
    let peers = state
        .peers
        .lock()
        .map_err(|_| "pk peers poisoned".to_string())?;
    Ok(peers.clone())
}
