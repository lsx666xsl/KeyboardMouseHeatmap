/**
 * KeyPulse Cloud — self-hosted account + duel relay server.
 *
 * Run:  npm install ws && node pk-cloud-server.js   (PORT env, default 7788)
 *
 * REST API (JSON):
 *   POST /api/register      { name, pass }            -> { ok, token?, error? }
 *   POST /api/login         { name, pass }            -> { ok, token, profile? } | { ok:false, error }
 *   GET  /api/me?token=..                            -> { name, best, wins, losses, games }
 *   POST /api/result        { token, win, score }     -> updated profile
 *   GET  /api/leaderboard                             -> [{ name, best, wins, losses, games }] top 50
 *   POST /api/logout        { token }
 *
 * WebSocket (duel relay, room of 2):
 *   join with ?token= and room:  ws://host:PORT/ws?token=..&room=any
 *   (same {t:"count"|"tick"|"peer"|"ended"} frames as before)
 *
 * Accounts persist to users.json next to the server (passwords hashed with
 * salt + sha256, no plaintext stored). Sessions are in-memory; restarting the
 * server logs everyone out (tokens re-issued on next login).
 */
"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { WebSocketServer } = require("ws");

const PORT = Number(process.env.PULSE_PORT || 7788);
const DATA_FILE = path.join(__dirname, "users.json");
const DURATION = 60;

let users = {}; // name -> { salt, hash, best, wins, losses, games }
let sessions = new Map(); // token -> name
const rooms = new Map(); // roomId -> { players: Map<ws,{name,count}>, timer }

function loadUsers() {
  try {
    users = JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));
  } catch {
    users = {};
  }
}
function saveUsers() {
  fs.writeFileSync(DATA_FILE, JSON.stringify(users, null, 2));
}
function hashPass(pass, salt) {
  return crypto.createHash("sha256").update(salt + ":" + pass).digest("hex");
}
function publicProfile(name) {
  const u = users[name];
  if (!u) return null;
  return { name, best: u.best, wins: u.wins, losses: u.losses, games: u.games };
}

function json(res, code, body) {
  const text = JSON.stringify(body);
  res.writeHead(code, {
    "content-type": "application/json; charset=utf-8",
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "content-type",
  });
  res.end(text);
}
function readBody(req) {
  return new Promise((resolve) => {
    let data = "";
    req.on("data", (c) => { data += c; if (data.length > 1e6) req.destroy(); });
    req.on("end", () => {
      try { resolve(JSON.parse(data || "{}")); } catch { resolve({}); }
    });
  });
}

const server = http.createServer(async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  const url = new URL(req.url, "http://localhost");
  const route = url.pathname;
  try {
    if (route === "/api/register" && req.method === "POST") {
      const { name, pass } = await readBody(req);
      const clean = String(name || "").trim().slice(0, 16);
      if (!/^[\w\u4e00-\u9fa5]{2,16}$/.test(clean)) {
        return json(res, 400, { ok: false, error: "昵称需 2-16 位中文/字母/数字" });
      }
      if (String(pass || "").length < 4) {
        return json(res, 400, { ok: false, error: "密码至少 4 位" });
      }
      if (users[clean]) return json(res, 409, { ok: false, error: "该昵称已被注册" });
      const salt = crypto.randomBytes(8).toString("hex");
      users[clean] = { salt, hash: hashPass(pass, salt), best: 0, wins: 0, losses: 0, games: 0 };
      saveUsers();
      const token = crypto.randomBytes(16).toString("hex");
      sessions.set(token, clean);
      return json(res, 200, { ok: true, token, profile: publicProfile(clean) });
    }
    if (route === "/api/login" && req.method === "POST") {
      const { name, pass } = await readBody(req);
      const clean = String(name || "").trim();
      const user = users[clean];
      if (!user || user.hash !== hashPass(String(pass || ""), user.salt)) {
        return json(res, 401, { ok: false, error: "昵称或密码不对" });
      }
      const token = crypto.randomBytes(16).toString("hex");
      sessions.set(token, clean);
      return json(res, 200, { ok: true, token, profile: publicProfile(clean) });
    }
    if (route === "/api/me") {
      const token = url.searchParams.get("token") || "";
      const name = sessions.get(token);
      if (!name) return json(res, 401, { ok: false, error: "未登录或登录已过期" });
      return json(res, 200, { ok: true, profile: publicProfile(name) });
    }
    if (route === "/api/result" && req.method === "POST") {
      const { token, win, score } = await readBody(req);
      const name = sessions.get(String(token || ""));
      if (!name) return json(res, 401, { ok: false, error: "未登录" });
      const u = users[name];
      u.games += 1;
      if (win) u.wins += 1; else u.losses += 1;
      if (Number(score) > u.best) u.best = Number(score);
      saveUsers();
      return json(res, 200, { ok: true, profile: publicProfile(name) });
    }
    if (route === "/api/leaderboard") {
      const list = Object.values(users)
        .map((u, i) => ({ name: Object.keys(users)[i], ...u }))
        .sort((a, b) => b.best - a.best || b.wins - a.wins)
        .slice(0, 50)
        .map((u) => ({ name: u.name, best: u.best, wins: u.wins, losses: u.losses, games: u.games }));
      return json(res, 200, { ok: true, list });
    }
    if (route === "/api/logout" && req.method === "POST") {
      const { token } = await readBody(req);
      sessions.delete(String(token || ""));
      return json(res, 200, { ok: true });
    }
    res.writeHead(200, { "content-type": "text/plain; charset=utf-8" });
    res.end("KeyPulse cloud server: REST auth APIs + duel relay\n");
  } catch (error) {
    json(res, 500, { ok: false, error: String(error) });
  }
});

const wss = new WebSocketServer({ server, path: "/ws" });
wss.on("connection", (ws, req) => {
  const url = new URL(req.url, "http://localhost");
  const token = url.searchParams.get("token") || "";
  const name = sessions.get(token);
  const roomId = url.searchParams.get("room") || "default";
  if (!name) {
    ws.close(4001, "unauthorized");
    return;
  }
  let room = rooms.get(roomId);
  if (!room) { room = { players: new Map(), timer: null }; rooms.set(roomId, room); }
  if (room.players.size >= 2) {
    ws.send(JSON.stringify({ t: "error", message: "房间已满" }));
    return;
  }
  room.players.set(ws, { name, count: 0 });
  ws.send(JSON.stringify({ t: "joined", name, room: roomId }));
  broadcast(room, { t: "peerJoined", name }, ws);
  if (room.players.size === 2) {
    startClock(room);
    broadcast(room, { t: "started", seconds: DURATION });
  }
  ws.on("message", (raw) => {
    let msg;
    try { msg = JSON.parse(raw.toString()); } catch { return; }
    if (msg.t === "count") {
      const player = room.players.get(ws);
      if (!player) return;
      player.count = Number(msg.v) || 0;
      for (const [other, otherPlayer] of room.players) {
        if (other !== ws) other.send(JSON.stringify({ t: "peer", name: player.name, v: player.count }));
      }
    }
  });
  ws.on("close", () => {
    room.players.delete(ws);
    if (room.players.size === 0) {
      clearInterval(room.timer);
      for (const [id, candidate] of rooms) if (candidate === room) rooms.delete(id);
    } else {
      broadcast(room, { t: "peerLeft" }, null);
    }
  });
});
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
    broadcast(room, { t: "tick", left }, null);
    if (left <= 0) {
      clearInterval(room.timer);
      room.timer = null;
      broadcast(room, { t: "ended" }, null);
    }
  }, 1000);
}

loadUsers();
server.listen(PORT, "0.0.0.0", () => {
  console.log(`KeyPulse cloud server on 0.0.0.0:${PORT} (REST /api/* + WS /ws)`);
});
