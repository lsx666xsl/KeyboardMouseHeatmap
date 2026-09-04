/**
 * KeyPulse Cloud — self-hosted account + duel relay server.
 *
 * Run:  npm install ws && node pk-cloud-server.js   (PORT env, default 7788)
 *
 * REST API (JSON):
 *   POST /api/register      { name, pass }             -> { ok, token?, error? }
 *   POST /api/login         { name, pass }             -> { ok, token, profile? }
 *   GET  /api/me?token=..                             -> profile with day stats
 *   POST /api/stats         { token, date, keys, mouse }  upsert daily totals
 *   POST /api/result        { token, win, score }      -> PK stats (optional)
 *   GET  /api/leaderboard?sort=total|today|days|streak -> typing leaderboard
 *   POST /api/logout        { token }
 *
 * Leaderboard is about input data (total keys / today / active days / streak),
 * not real-time dueling: clients report their daily aggregate and the server
 * ranks everyone who plays. (A WS relay still exists for future duels.)
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

let users = {}; // name -> { salt, hash, best, wins, losses, games, days: {date:{k,m}} }
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
function dayStats(profile) {
  const days = profile.days || {};
  const entries = Object.entries(days).sort((a, b) => (a[0] < b[0] ? -1 : 1));
  const totalKeys = entries.reduce((s, [, d]) => s + (d.k || 0), 0);
  const totalMouse = entries.reduce((s, [, d]) => s + (d.m || 0), 0);
  const todayKey = new Date().toISOString().slice(0, 10);
  const today = days[todayKey] || { k: 0, m: 0 };
  // streak: consecutive days ending today (or yesterday)
  let streak = 0;
  const cursor = new Date();
  if (!days[cursor.toISOString().slice(0, 10)]) cursor.setDate(cursor.getDate() - 1);
  while (days[cursor.toISOString().slice(0, 10)]) {
    streak += 1;
    cursor.setDate(cursor.getDate() - 1);
  }
  return { totalKeys, totalMouse, activeDays: entries.length, streak, todayKeys: today.k || 0, todayMouse: today.m || 0, lastActive: entries.length ? entries[entries.length - 1][0] : null };
}

function publicProfile(name) {
  const u = users[name];
  if (!u) return null;
  const derived = dayStats(u);
  return { name, best: u.best || 0, wins: u.wins || 0, losses: u.losses || 0, games: u.games || 0, ...derived };
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
      users[clean] = { salt, hash: hashPass(pass, salt), best: 0, wins: 0, losses: 0, games: 0, days: {} };
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
    if (route === "/api/stats" && req.method === "POST") {
      const { token, date, keys, mouse } = await readBody(req);
      const name = sessions.get(String(token || ""));
      if (!name) return json(res, 401, { ok: false, error: "未登录" });
      const day = String(date || new Date().toISOString().slice(0, 10)).slice(0, 10);
      const u = users[name];
      u.days = u.days || {};
      const prev = u.days[day] || { k: 0, m: 0 };
      u.days[day] = { k: Math.max(prev.k, Number(keys) || 0), m: Math.max(prev.m, Number(mouse) || 0) };
      saveUsers();
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
      const sortBy = url.searchParams.get("sort") || "total";
      const rows = Object.keys(users).map((name) => {
        const profile = publicProfile(name);
        return { name, best: profile.best, wins: profile.wins, losses: profile.losses, games: profile.games, totalKeys: profile.totalKeys, totalMouse: profile.totalMouse, activeDays: profile.activeDays, streak: profile.streak, todayKeys: profile.todayKeys, lastActive: profile.lastActive };
      });
      rows.sort((a, b) => {
        if (sortBy === "today") return b.todayKeys - a.todayKeys || b.totalKeys - a.totalKeys;
        if (sortBy === "days") return b.activeDays - a.activeDays || b.totalKeys - a.totalKeys;
        if (sortBy === "streak") return b.streak - a.streak || b.totalKeys - a.totalKeys;
        return b.totalKeys - a.totalKeys || b.activeDays - a.activeDays;
      });
      return json(res, 200, { ok: true, list: rows.slice(0, 100) });
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
