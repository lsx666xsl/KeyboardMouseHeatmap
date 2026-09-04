# KeyPulse 云端服务器部署指南

`pk-cloud-server.js` 是纯 Node 应用（无框架依赖，仅 `ws`），可挂到任何 Linux/Windows
服务器或云主机长期运行。它提供：

- REST 账号 API（注册/登录/每日统计上报/排行榜/登出）
- WebSocket 对战房间（预留）

## 1. 上传与安装

```bash
# 在服务器上
git clone https://github.com/lsx666xsl/KeyboardMouseHeatmap.git   # 或直接上传 server/ 目录
cd KeyboardMouseHeatmap/server
npm install          # 只需安装 ws
node pk-cloud-server.js
# => KeyPulse cloud server on 0.0.0.0:7788
```

数据文件：`server/users.json`（账号+统计，密码为 scrypt 加盐哈希）。
**定期备份这个文件即可备份全部账号数据。**

## 2. 常驻运行（二选一）

### systemd（Linux 推荐）

```ini
# /etc/systemd/system/keypulse-cloud.service
[Unit]
Description=KeyPulse cloud server
After=network.target

[Service]
WorkingDirectory=/opt/KeyPulse/server
ExecStart=/usr/bin/node pk-cloud-server.js
Restart=always
RestartSec=3
Environment=PULSE_PORT=7788
User=keypulse

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now keypulse-cloud
sudo systemctl status keypulse-cloud
```

### pm2（跨平台方便）

```bash
npm install -g pm2
pm2 start pk-cloud-server.js --name keypulse-cloud
pm2 save && pm2 startup
pm2 logs keypulse-cloud
```

## 3. 防火墙

- 客户端直连：放行 TCP `7788`（`ufw allow 7788/tcp`），REST 与 WS 共用同一端口。
- 若本机只是开发测试：保持本机访问即可（客户端填 http://127.0.0.1:7788）。

## 4. 安全建议（公网部署必读）

1. **务必套 HTTPS**：登录密码会经网络传输。用 Nginx/Caddy 反向代理加 TLS：
   ```nginx
   # /etc/nginx/sites-enabled/keypulse
   server {
     listen 443 ssl;
     server_name kp.example.com;
     ssl_certificate     /etc/letsencrypt/live/kp.example.com/fullchain.pem;
     ssl_certificate_key /etc/letsencrypt/live/kp.example.com/privkey.pem;
     location / {
       proxy_pass http://127.0.0.1:7788;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;      # WebSocket 需要
       proxy_set_header Connection "upgrade";
     }
   }
   ```
   客户端服务器地址填：`https://kp.example.com`
2. 密码已用 **scrypt 加盐慢哈希**存储（不是明文/弱哈希），旧 sha256 账号登录后自动升级。
3. 会话 token 存内存：服务器重启后全员需重新登录（可接受的小成本）。
4. 建议开一个普通用户跑服务（示例中 `User=keypulse`），不要把服务跑在 root。
5. users.json 权限：`chmod 600 users.json`。

## 5. 客户端连接

⚙ 设置 → 云端账号 → 服务器地址填入你的地址 → 注册/登录。
登录后程序每 30 秒自动上报今日统计，云端排行即可见（⚙ → 云端账号面板）。
