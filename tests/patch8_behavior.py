"""Add launch & close behavior UI group to the settings modal."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# ---- script state + actions (place near data-location helpers) ----
anchor = "const dataLocation = ref(\"appdata\");"
assert anchor in t
block = anchor + """
const autostartOn = ref(false);
const startBehavior = ref("normal");
const closeBehavior = ref("tray");

async function refreshBehavior() {
  try {
    autostartOn.value = await invoke<boolean>("get_autostart");
    const [start, close] = await invoke<[string, string]>("get_app_behavior");
    startBehavior.value = start;
    closeBehavior.value = close;
  } catch {
    // older runtime
  }
}

async function toggleAutostart(on: boolean) {
  autostartOn.value = on;
  try {
    await invoke("set_autostart", { enabled: on });
  } catch (error) {
    autostartOn.value = !on;
    console.info("Could not change autostart.", error);
  }
}

async function changeBehavior(kind: "start" | "close", value: string) {
  if (kind === "start") startBehavior.value = value;
  else closeBehavior.value = value;
  try {
    await invoke("set_app_behavior", { start: startBehavior.value, close: closeBehavior.value });
  } catch (error) {
    console.info("Could not change behavior.", error);
  }
}"""
t = t.replace(anchor, block)

# refresh on settings open
old = """  refreshDataInfo();
  showSettingsPanel.value = true;"""
assert old in t
t = t.replace(old, """  refreshDataInfo();
  refreshBehavior();
  showSettingsPanel.value = true;""")

# ---- template group before 数据存储 section ----
old_section = """              <div class="ks-section-title">数据存储</div>"""
assert old_section in t
group = """              <div class="ks-section-title">启动与关闭</div>
              <div class="ks-behavior-row">
                <button class="ks-drag-toggle" :class="{ on: autostartOn }" @click="toggleAutostart(!autostartOn)"><span class="ks-master-text"><b>{{ autostartOn ? "开机自启动已开" : "开机自启动已关" }}</b><small>{{ autostartOn ? "登录 Windows 后自动在后台运行" : "开机时不会自动启动" }}</small></span><span class="ks-switch"><i></i></span></button>
              </div>
              <div class="ks-radio-row">
                <span class="ks-radio-label">启动时</span>
                <div class="ks-radios" role="radiogroup" aria-label="启动方式">
                  <button v-for="opt in [{ id: 'normal', name: '显示窗口' }, { id: 'minimized', name: '最小化' }, { id: 'tray', name: '后台托盘' }]" :key="opt.id" class="ks-radio" :class="{ active: startBehavior === opt.id }" role="radio" :aria-checked="startBehavior === opt.id" @click="changeBehavior('start', opt.id)">{{ opt.name }}</button>
                </div>
              </div>
              <div class="ks-radio-row">
                <span class="ks-radio-label">关闭时</span>
                <div class="ks-radios" role="radiogroup" aria-label="关闭按钮行为">
                  <button v-for="opt in [{ id: 'tray', name: '隐藏到托盘' }, { id: 'minimize', name: '最小化' }, { id: 'quit', name: '退出' }]" :key="opt.id" class="ks-radio" :class="{ active: closeBehavior === opt.id }" role="radio" :aria-checked="closeBehavior === opt.id" @click="changeBehavior('close', opt.id)">{{ opt.name }}</button>
                </div>
              </div>
              <div class="ks-section-title">数据存储</div>"""
t = t.replace(old_section, group)

# ---- css ----
anchor_css = ".ks-data { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }"
assert anchor_css in t
css = anchor_css + """
.ks-behavior-row { margin-bottom: 8px; }
.ks-radio-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.ks-radio-label { flex: 0 0 52px; color: var(--tx-faint); font-size: 10px; font-weight: 700; }
.ks-radios { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; flex: 1; }
.ks-radio { padding: 7px 0; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 9px; color: var(--tx-soft); background: rgba(var(--ink-rgb), .3); cursor: pointer; font-size: 10px; }
.ks-radio:hover { border-color: rgba(var(--cyan-rgb), .55); color: var(--text-main); }
.ks-radio.active { border-color: rgba(var(--cyan-rgb), .7); color: #fff; background: rgba(var(--cyan-rgb), .16); }
html[data-theme="starlight"] .ks-radio.active, html[data-theme="latte"] .ks-radio.active, html[data-theme="sage"] .ks-radio.active, html[data-theme="matcha"] .ks-radio.active { color: #1d1d1f; }
"""
t = t.replace(anchor_css, css)

p.write_text(t, encoding="utf-8")
print("launch/close group added")
