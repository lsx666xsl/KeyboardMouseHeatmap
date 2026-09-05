"""Restructure settings modal: left nav + categorized panes; add login portal wiring."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)

def find_line(fragment, start=0):
    for i in range(start, len(lines)):
        if fragment in lines[i]:
            return i
    return -1

head_i = find_line("ks-modal-head")
profile_i = find_line('ks-section-title">我的档案', head_i)
cloud_i = find_line("<CloudAccount />", head_i)
theme_i = find_line('ks-section-title">主题配色', head_i)
keyshow_i = find_line('ks-section-title">按键可视化', head_i)
mini_i = find_line('ks-section-title">迷你统计窗', head_i)
startup_i = find_line('ks-section-title">启动与关闭', head_i)
data_i = find_line('ks-section-title">数据存储', head_i)
fun_i = find_line('ks-section-title">趣味功能', head_i)
note_i = find_line("ks-note", fun_i)
close_i = find_line("</section>", note_i)
assert -1 not in (head_i, profile_i, cloud_i, theme_i, keyshow_i, mini_i, startup_i, data_i, fun_i, note_i, close_i), "anchor missing"

g_profile = lines[profile_i:cloud_i]
g_cloud = lines[cloud_i:theme_i]
g_theme = lines[theme_i:keyshow_i]
g_keyshow = lines[keyshow_i:mini_i]
g_mini = lines[mini_i:startup_i]
g_startup = lines[startup_i:data_i]
g_data = lines[data_i:fun_i]
g_fun = lines[fun_i:note_i]
note = lines[note_i]

portal_btn = """              <button class="portal-open" @click="showLoginPortal = true"><i>⚡</i><span><b>登录 / 连接服务器</b><small>云端账号 · 局域网发现 · 数据排行</small></span><em>›</em></button>
"""

def pane(name, *groups, extra=""):
    body = "".join(groups)
    return f'              <section v-show="settingsTab === \'{name}\'" class="ks-pane">\n{body}{extra}              </section>\n'

account_pane = pane("account", "".join(g_profile), portal_btn, "".join(g_cloud))
theme_pane = pane("theme", "".join(g_theme))
keyshow_pane = pane("keyshow", "".join(g_keyshow), "".join(note))
widgets_pane = pane("widgets", "".join(g_mini))
system_pane = pane("system", "".join(g_startup), "".join(g_data))
fun_pane = pane("fun", "".join(g_fun))

nav = """              <div class="ks-body">
                <nav class="ks-nav" aria-label="设置分类">
                  <button v-for="tab in settingsTabs" :key="tab.id" :class="{ active: settingsTab === tab.id }" @click="settingsTab = tab.id"><i>{{ tab.icon }}</i><span>{{ tab.name }}</span></button>
                </nav>
                <div class="ks-panes">
"""
new_body = (
    nav
    + account_pane + theme_pane + keyshow_pane + widgets_pane + system_pane + fun_pane
    + "                </div>\n              </div>\n"
)

# replace everything between head line and close line
lines[head_i + 1:close_i] = [new_body]
p.write_text("".join(lines), encoding="utf-8")
print("modal restructured into nav panes")
