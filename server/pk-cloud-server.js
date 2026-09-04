/**
 * KeyPulse Cloud Duel relay — self-hosted room server for the typing duel.
 *
 * How to run:
 *   node pk-cloud-server.js            # listens on 0.0.0.0:7788
 *   PULSE_PORT=9000 node pk-cloud-server.js
 *
 * Protocol (WebSocket JSON):
 *   client -> { t: "join", room: "any", name: "Alice" }
 *   client -> { t: "count", v: 123 }            (every ~1s while dueling)
 *   server -> { t: "peer", name: "Bob", v: 111 }
 *   server -> { t: "tick", left: 42 }
 *   client -> { t: "leave" }
 *
 * A "duel" is simply two clients in the same room. The server relays counts
 * and runs the 60s clock when the second player joins. No accounts, no
 * storage: the server is stateless and forgets everything on restart.
 *
 * To wire the desktop client to this server later: add a "cloud" transport in
 * src-tauri/src/pk.rs that opens a WebSocket instead of the LAN TCP channel —
 * the message shapes above already match the LAN relay format.
 */
"use strict";

const http = require("http");
const { WebSocketServer } = require("ws");

const PORT = Number(process.env.PULSE_PORT || 7788);
const DURATION = 60;

const rooms = new Map(); // roomId -> { players: Map<ws, {name, count, clock?}> , timer }

function roomOf(ws) {
  for (const room of rooms.values()) {
    if (room.players.has(ws)) return room;
  }
  return null;
}

function broadcast(room, msg, except) {
  const text = JSON.stringify(msg);
  for (const ws of room.players.keys()) {
    if (ws !== except && ws.readyState === ws.OPEN) ws.send(text);
  }
}

function startClock(room) {
  if (room.timer) return;
  let left = DURATION;
  room.timer = setInterval(() => {
    left -= 1;
    broadcast(room, { t: "tick", left });
    if (left <= 0) {
      clearInterval(room.timer);
      room.timer = null;
      broadcast(room, { t: "ended" });
    }
  }, 1000);
}

const server = http.createServer((req, res) => {
  res.writeHead(200, { "content-type": "text/plain; charset=utf-8" });
  res.end("KeyPulse cloud duel relay is running\n");
});

const wss = new WebSocketServer({ server });

wss.on("connection", (ws) => {
  ws.on("message", (raw) => {
    let msg;
    try {
      msg = JSON.parse(raw.toString());
    } catch {
      return;
    }
    if (msg.t === "join") {
      const roomId = msg.room || "default";
      let room = rooms.get(roomId);
      if (!room) {
        room = { players: new Map(), timer: null };
        rooms.set(roomId, room);
      }
      if (room.players.size >= 2) {
        ws.send(JSON.stringify({ t: "error", message: "房间已满，等待旁观者离开" }));
        return;
      }
      room.players.set(ws, { name: String(msg.name || "玩家").slice(0, 16), count: 0 });
      broadcast(room, { t: "joined", players: [...room.players.values()].map((p) => p.name) });
      if (room.players.size === 2) {
        startClock(room);
        broadcast(room, { t: "started", seconds: DURATION });
      }
    } else if (msg.t === "count") {
      const room = roomOf(ws);
      if (!room) return;
      const player = room.players.get(ws);
      if (!player) return;
      player.count = Number(msg.v) || 0;
      for (const [other, otherPlayer] of room.players) {
        if (other !== ws) {
          other.send(JSON.stringify({ t: "peer", name: player.name, v: player.count }));
        }
      }
    } else if (msg.t === "leave") {
      const room = roomOf(ws);
      if (room) {
        room.players.delete(ws);
        if (room.players.size === 0) {
          clearInterval(room.timer);
          rooms.delete(roomOf(ws).players.size === 0 ? [...rooms.keys()].find((k) => rooms.get(k) === room) : "default");
        } else {
          broadcast(room, { t: "peerLeft" });
        }
      }
    }
  });

  ws.on("close", () => {
    const room = roomOf(ws);
    if (!room) return;
    room.players.delete(ws);
    if (room.players.size === 0) {
      clearInterval(room.timer);
      for (const [id, candidate] of rooms) {
        if (candidate === room) rooms.delete(id);
      }
    } else {
      broadcast(room, { t: "peerLeft" });
    }
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`KeyPulse cloud duel relay listening on 0.0.0.0:${PORT}`);
});
