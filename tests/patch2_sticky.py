"""Replay patch 2: sticky floating topbar + standalone gear button."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# sticky floating topbar (extend the stacking-fix block)
old = ".topbar { z-index: 3; }.hero-row { z-index: 2; }.runtime-warning { z-index: 4; }"
new = (
    ".topbar { z-index: 5; }.hero-row { z-index: 2; }.runtime-warning { z-index: 4; }\n"
    ".topbar { position: sticky; top: 10px; padding: 9px 16px; border: 1px solid rgba(var(--line-rgb), .14); border-radius: 18px; background: rgba(var(--pop-rgb), .8); backdrop-filter: blur(16px); box-shadow: 0 12px 32px rgba(0, 0, 0, .16); margin-bottom: 26px; }\n"
    'html[data-theme="starlight"] .topbar { box-shadow: 0 12px 30px rgba(0, 0, 0, .08); }'
)
assert old in t, "stacking block missing"
t = t.replace(old, new)

# gear button styling independent
old_btn = ".settings-button { display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid rgba(148,163,184,.15); border-radius: 999px; background: rgba(var(--panel-rgb),.55); color: #7e8eae; cursor: pointer; font-size: 14px; transition: all .2s ease; }"
new_btn = ".settings-button { display: grid; place-items: center; flex: 0 0 auto; width: 36px; height: 36px; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 999px; background: rgba(var(--panel-rgb), .6); color: var(--tx-faint); cursor: pointer; font-size: 16px; transition: all .25s ease; }"
assert old_btn in t, "settings button css missing"
t = t.replace(old_btn, new_btn)
old_hover = ".settings-button:hover { border-color: rgba(var(--cyan-rgb),.7); color: #fff; transform: rotate(40deg); }"
new_hover = ".settings-button:hover { border-color: rgba(var(--cyan-rgb), .8); color: var(--text-main); transform: rotate(90deg) scale(1.05); box-shadow: 0 0 16px rgba(var(--cyan-rgb), .25); }"
assert old_hover in t, "settings hover css missing"
t = t.replace(old_hover, new_hover)

p.write_text(t, encoding="utf-8")
print("patch2 applied")
