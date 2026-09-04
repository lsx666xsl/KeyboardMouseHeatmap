# GUI 验收辅助脚本

这些脚本用于对本机运行的 KeyPulse release 程序做黑盒验收（真实 Hook、托盘、WebView UI）。
核心思路：`--remote-debugging-port=9222` 启动 WebView2，用 CDP 读取/驱动页面；用 Win32
合成输入（SendInput/mouse_event）操作托盘与原生菜单。应用本身会忽略注入的键鼠事件，
因此合成输入不会污染统计（这也是验收项之一）。

## 常用流程

```powershell
# 启动带 CDP 的应用并确认存活
powershell -ExecutionPolicy Bypass -File tests\start-with-cdp.ps1

# 停止应用 / 查询是否在运行
powershell -ExecutionPolicy Bypass -File tests\app-lifecycle.ps1 -Action stop|check

# 在页面执行任意 JS 并打印结果（用于断言 UI 状态）
python tests/cdp_eval.py "document.querySelector('.demo-chip')?.textContent"

# 托盘菜单动作：打开溢出弹层 -> 右键 KeyPulse 图标 -> Down xN + Enter
#   Downs=1 打开窗口  2 暂停/继续  3 清空本地统计  4 退出应用
powershell -ExecutionPolicy Bypass -File tests\tray-menu-action.ps1 -Downs 2 -Label toggle

# 合成左/右键点击（验证注入过滤：点击后统计不应增加）
powershell -ExecutionPolicy Bypass -File tests\click-at.ps1 -X 600 -Y 90 -Button left
```

## 注意事项

- `click-at.ps1` / `send-keys.ps1` 是注入输入，用于验证应用对注入事件的过滤，以及操作系统托盘；
  真实计数的验收请直接使用真实键盘鼠标。
- 托盘图标可能在通知区或溢出弹层中，坐标会随任务栏变化；`tray-menu-action.ps1` 会先解析图标位置。
- `install-msi.ps1` 需要管理员权限（MSI 写入 HKLM/Program Files），无提权时会以 1603 失败。
- 坐标/窗口位置基于本机 3840x2160 @ 300% DPI；换机器需要重新标定。
