# KeyPulse 云端对战中继（自托管）

`pk-cloud-server.js` 是一个无状态 WebSocket 中继：同一房间两名玩家互相转发按键计数，
服务端负责 60 秒倒计时。没有账号、不存数据，重启即清零。

## 运行

```bash
npm init -y && npm install ws        # 只需要 ws 一个依赖
node pk-cloud-server.js              # 默认 0.0.0.0:7788
PULSE_PORT=9000 node pk-cloud-server.js
```

局域网直接用「PK 对战 → 开启对战等待挑战」即可；跨网络（不在同一 WiFi）时才需要本服务。
把服务部署到有公网 IP 的机器/云主机后，桌面端后续接入「云端房间」传输层
（`src-tauri/src/pk.rs` 增加 WebSocket 通道，消息格式与现局域网中继一致）。
