# 备份说明

## 备份策略

- Git 用于保存开发历史和可回退版本
- `backups` 用于保存重要里程碑的压缩快照
- 快照命名格式：`YYYY-MM-DD-stage-name.zip`
- 每完成一个开发阶段至少创建一次快照
- 重大技术决策变更前先创建快照

## 不应放入备份的内容

- `node_modules`
- Rust `target` 目录
- 运行时 SQLite 数据库
- 原始输入事件日志
- 包含个人信息的调试输出

## 当前备份

- [x] 规划阶段快照：`backups/2026-09-04-planning.zip`
- [x] Tauri 基础工程/可视化原型快照：`backups/2026-09-04-tauri-prototype.zip`
- [x] 输入监听 + SQLite 阶段快照：`backups/2026-09-04-input-storage.zip`
- [x] 日期范围与清空控制快照：`backups/2026-09-04-dashboard-range.zip`
- [x] 系统托盘阶段快照：`backups/2026-09-04-tray.zip`
- [x] 自定义日期范围阶段快照：`backups/2026-09-04-custom-date.zip`
- [x] Windows 安装包阶段快照：`backups/2026-09-04-windows-packaging.zip`
- [ ] MVP 完成快照

每次创建快照后，在 `notes/开发日志.md` 和 `notes/交接说明.md` 中记录文件名及对应 Git commit。
