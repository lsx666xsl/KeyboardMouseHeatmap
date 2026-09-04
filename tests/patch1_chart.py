"""Replay patch 1: activity pulse chart baseline fix."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

old_tpl = '<div class="chart-bar" :style="{ height: `${value}%` }"><span>{{ value }}</span></div><small v-if="hour % 3 === 0">{{ String(hour).padStart(2, "0") }}:00</small>'
new_tpl = '<div class="chart-bar" :style="{ height: `${value * 0.84}%` }"><span>{{ value }}</span></div><small v-if="hour % 3 === 0">{{ String(hour).padStart(2, "0") }}:00</small>'
assert old_tpl in t, "chart template missing"
t = t.replace(old_tpl, new_tpl)

old_css = ".chart-column { position: relative; z-index: 1; display: flex; flex: 1; height: 100%; flex-direction: column; align-items: center; justify-content: end; gap: 8px; }.chart-bar { position: relative; width: min(100%,30px); min-height: 5px; border-radius: 6px 6px 2px 2px; background: linear-gradient(180deg,var(--acc-pink-bright),var(--acc-violet) 75%,var(--bar-tip)); opacity: .85; transition: height .25s ease,opacity .2s ease; }.chart-bar:hover { opacity: 1; }.chart-bar span { position: absolute; top: -17px; left: 50%; display: none; color: var(--text-main); font-size: 8px; transform: translateX(-50%); }.chart-bar:hover span { display: block; }.chart-column small { height: 12px; color: var(--tx-mute); font-size: 8px; }"
new_css = ".chart-column { position: relative; z-index: 1; display: flex; flex: 1; height: 100%; flex-direction: column; align-items: center; justify-content: flex-end; }.chart-bar { position: relative; width: min(100%,30px); min-height: 5px; margin-bottom: 15px; border-radius: 6px 6px 2px 2px; background: linear-gradient(180deg,var(--acc-pink-bright),var(--acc-violet) 75%,var(--bar-tip)); opacity: .85; transition: height .25s ease,opacity .2s ease; }.chart-bar:hover { opacity: 1; }.chart-bar span { position: absolute; top: -17px; left: 50%; display: none; color: var(--tx-soft); font-size: 8px; transform: translateX(-50%); white-space: nowrap; }.chart-bar:hover span { display: block; }.chart-column small { position: absolute; bottom: 0; left: 0; right: 0; height: 12px; color: var(--tx-mute); font-size: 8px; text-align: center; }"
assert old_css in t, "chart css missing"
t = t.replace(old_css, new_css)

p.write_text(t, encoding="utf-8")
print("patch1 applied")
