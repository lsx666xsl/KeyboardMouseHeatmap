"""Replay patch 3b: fun-feature settings UI + achievement toast markup/styles."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# 1. fun section before the ks-note line (settings modal tail)
note = '<p class="ks-note">⌨ 显示的是按下动作，不记录文本 · 托盘菜单或顶栏 ⌨ 按钮可随时开/关 · 拖动后选择任意预设位置可恢复对齐</p>'
assert note in t, "ks-note missing"
fun_block = """              <div class="ks-section-title">趣味功能</div>
              <div class="ks-layout-row">
                <div class="ks-layout-col"><div class="ks-layout-title">打字音效</div>
                  <div class="ks-sound-row">
                    <select class="ks-select" :value="soundVoice" @change="setSoundVoice(($event.target as HTMLSelectElement).value as SoundVoice)">
                      <option value="off">关闭</option><option value="click">机械青轴</option><option value="typewriter">打字机</option><option value="bubble">泡泡</option>
                    </select>
                    <label class="ks-range compact"><input type="range" min="0" max="100" step="5" :value="soundVolume" :disabled="soundVoice === 'off'" @input="setSoundVolume(Number(($event.target as HTMLInputElement).value))" /><span>{{ soundVolume }}</span></label>
                  </div>
                </div>
                <div class="ks-layout-col"><div class="ks-layout-title">成就提示</div>
                  <button class="ks-drag-toggle" :class="{ on: achievementsOn }" @click="toggleAchievements(!achievementsOn)"><span class="ks-master-text"><b>{{ achievementsOn ? "已开启" : "已关闭" }}</b><small>当日 1k / 5k / 1w / 5w 键里程碑弹提示</small></span><span class="ks-switch"><i></i></span></button>
                </div>
              </div>
"""
t = t.replace(note, fun_block + note)

# 2. achievement toast host right before footer
footer = '<footer class="footer-note">'
assert footer in t, "footer missing"
toast = (
    '<Transition name="toast-pop"><div v-if="toastMsg" class="achievement-toast" role="status"><span>🏆</span><div><b>成就达成</b><small>{{ toastMsg }}</small></div></div></Transition>\n'
    '    <footer class="footer-note">'
)
t = t.replace(footer, toast, 1)

# 3. styles appended after ks-data-notice rule
anchor_css = ".ks-data-notice { margin: 8px 0 0; padding: 8px 10px; border-radius: 8px; color: var(--acc-amber); background: rgba(var(--amber-rgb), .08); font-size: 9px; line-height: 1.5; }"
assert anchor_css in t, "ks-data-notice css missing"
extra_css = anchor_css + """
.ks-sound-row { display: flex; flex-direction: column; gap: 6px; }
.ks-select { width: 100%; padding: 7px 9px; border: 1px solid rgba(var(--line-rgb), .25); border-radius: 9px; color: var(--tx-strong); background: rgba(var(--ink-rgb), .35); font-size: 11px; cursor: pointer; }
.ks-range.compact { padding: 5px 8px; }
.achievement-toast { position: fixed; z-index: 40; right: 22px; bottom: 26px; display: flex; align-items: center; gap: 10px; max-width: 320px; padding: 12px 16px; border: 1px solid rgba(var(--amber-rgb), .4); border-radius: 14px; background: rgba(var(--pop-rgb), .92); backdrop-filter: blur(14px); box-shadow: 0 16px 44px rgba(0, 0, 0, .3); }
.achievement-toast > span { font-size: 20px; }
.achievement-toast b, .achievement-toast small { display: block; }
.achievement-toast b { color: var(--text-main); font-size: 12px; }
.achievement-toast small { margin-top: 3px; color: var(--tx-soft); font-size: 11px; line-height: 1.45; }
.toast-pop-enter-active { transition: all .35s cubic-bezier(.2, 1.4, .4, 1); }
.toast-pop-leave-active { transition: all .25s ease; }
.toast-pop-enter-from, .toast-pop-leave-to { opacity: 0; transform: translateY(16px) scale(.92); }
"""
t = t.replace(anchor_css, extra_css)

p.write_text(t, encoding="utf-8")
print("patch3b applied")
