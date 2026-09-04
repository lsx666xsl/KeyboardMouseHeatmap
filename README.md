<div align="center">

# KeyPulse

<p><strong>Keyboard & Mouse Heatmap</strong></p>
<p>把每一次敲击、点击和滚动，变成看得见的节奏。</p>

<p>
  <code>Tauri 2</code>
  <code>Rust</code>
  <code>Vue 3</code>
  <code>TypeScript</code>
  <code>SQLite</code>
</p>

</div>

<section>

## 项目简介

KeyPulse 是一个 Windows 优先、离线运行的键盘和鼠标使用统计可视化工具。
它会将按键次数、鼠标操作和时间活跃度呈现在键盘模板、鼠标模板和趋势图上，帮助用户直观看到自己的输入节奏。

</section>

<section>

## 当前进度

<table>
  <thead>
    <tr><th>阶段</th><th>状态</th><th>说明</th></tr>
  </thead>
  <tbody>
    <tr><td>项目规划</td><td>✅ 已完成</td><td>需求、架构、开发流程和交接规范已建立</td></tr>
    <tr><td>阶段备份</td><td>✅ 已完成</td><td>已生成规划阶段快照</td></tr>
    <tr><td>Tauri 基础工程</td><td>✅ 构建已验证</td><td>前端、Rust 测试、release exe、MSI 和 NSIS 均已通过</td></tr>
    <tr><td>输入监听</td><td>🔄 已实现待验收</td><td>Rust Windows Hook 已完成，默认过滤注入事件和自动重复；失败时界面会提示</td></tr>
    <tr><td>热力图界面</td><td>🔄 已接入接口</td><td>演示页已连接 SQLite 查询和 stats-updated 实时事件，待人工验收</td></tr>
    <tr><td>日期筛选</td><td>🔄 已实现待验收</td><td>支持预设范围和自定义开始/结束日期</td></tr>
    <tr><td>系统托盘</td><td>🔄 已实现待验收</td><td>支持打开窗口、关闭隐藏、暂停/继续、清空统计和退出</td></tr>
    <tr><td>隐私与权限说明</td><td>✅ 已验收</td><td>头像按钮打开说明弹窗，聚焦/关闭/内容均已验证</td></tr>
    <tr><td>主题配色</td><td>✅ 已实现</td><td>4 套主题可切换并持久化，热力图与图例联动</td></tr>
    <tr><td>按键可视化</td><td>🔄 已实现待观感验收</td><td>实时显示按下的键：节奏胶囊/能量粒子/迷你键盘三风格，托盘与顶栏可开关</td></tr>
    <tr><td>系统托盘验收</td><td>✅ 已验收</td><td>打开/关闭隐藏/暂停/清空/退出均实测通过</td></tr>
  </tbody>
</table>

</section>

<section>

## 目标功能

- 键盘各按键次数统计
- 鼠标左键、右键、中键、侧键和滚轮统计
- 键盘模板上的动态热力颜色和具体次数
- 鼠标模板上的按钮数据展示
- 今日、本周、本月和自定义时间范围
- 总量、活跃时段、高频按键和趋势图
- 活泼、丰富、年轻化的可视化主题
- 4 套可切换配色（霓虹之夜、深海回声、落日熔金、极光森林），选择会记住
- 实时按键可视化：按下按键时屏幕底部显示按键（录屏/演示/教学友好），三种风格可切换
- 系统托盘后台运行、暂停/继续记录
- 本地离线运行，不保存完整输入文本
- 过滤注入键鼠事件，统计只反映真实物理输入

</section>

<section>

## 技术架构

```text
Windows 键盘/鼠标事件
          ↓
Rust 原生监听与统计聚合
          ↓
SQLite 本地保存聚合数据
          ↓
Tauri Command / Event
          ↓
Vue 3 仪表盘
          ↓
SVG 键盘/鼠标模板 + ECharts 趋势图
```

| 模块 | 技术 | 职责 |
|---|---|---|
| 桌面容器 | Tauri 2 | 窗口、托盘、通信和打包 |
| 原生后端 | Rust stable | 输入监听、统计聚合、数据库访问 |
| Windows 集成 | `windows` crate | `WH_KEYBOARD_LL` / `WH_MOUSE_LL` |
| 前端 | Vue 3 + TypeScript + Vite | 仪表盘和交互 |
| 数据库 | SQLite | 保存日期/小时/按键聚合统计 |
| 图表 | ECharts | 趋势图和时间热力图 |
| 模板 | SVG + CSS | 键盘、鼠标和颜色映射 |

</section>

<section>

## 隐私原则

<blockquote>
默认只保存统计结果，不保存用户实际输入的文本内容。
</blockquote>

- 不保存完整按键序列
- 不保存密码、聊天内容或文档内容
- 默认过滤系统自动重复按键
- 默认不保存鼠标坐标
- 应用分类统计如启用，也只保存应用类别，不保存窗口标题
- 用户可以暂停记录和清空本地数据
- 主界面头像按钮可打开“隐私与权限说明”弹窗，应用内即可查看数据行为和 Hook 权限限制

</section>

<section>

## 本地开发

```powershell
npm install
npm run dev
```

运行 Tauri 桌面应用：

```powershell
npm run tauri dev
```

构建前端：

```powershell
npm run build
```

构建桌面发布包：

```powershell
npm run tauri build
```

</section>

<section>

## 项目文档

- [需求清单](docs/需求清单.md)：所有需求和验收标准，使用复选框标记状态
- [开发流程与总体方案](docs/开发流程.md)：架构、阶段、开发规范和退出条件
- [技术决策记录](docs/技术决策记录.md)：重要技术选择及原因
- [人工验收清单](docs/人工验收清单.md)：真实键盘、鼠标、暂停和持久化测试步骤
- [开发日志](notes/开发日志.md)：已完成内容、验证结果、问题和下一步
- [交接说明](notes/交接说明.md)：其他 agent 接手时的阅读顺序和当前状态
- [备份说明](backups/README.md)：Git 和阶段压缩快照规则

</section>

<section>

## 项目位置与仓库

- 本地目录：`F:\TauriProject\KeyboardMouseHeatmap`
- Git 远程仓库：`git@github.com:lsx666xsl/KeyboardMouseHeatmap.git`
- 默认分支：`main`

</section>

<div align="center">

<sub>KeyPulse · offline by design · privacy first</sub>

</div>
