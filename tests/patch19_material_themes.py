"""Add material themes: jade (polished stone keycaps) and wood (grain keycaps)."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

anchor = "/* lavender 薰衣草 — soft powdery purple on pale paper */"
assert anchor in t

themes = """
/* jade 玉石 — polished translucent green stone with gem sheen */
html[data-theme="jade"] {
  --page-bg: #10201a; --page-glow: rgba(127, 222, 178, .16);
  --acc-pink: #6fcfa8; --acc-pink-bright: #8fdfb9; --acc-pink-soft: #b4ecd2;
  --acc-cyan: #6fc3c0; --acc-cyan-bright: #8dd4d1;
  --acc-violet: #a8c5b5; --acc-green: #8fe0b5; --acc-amber: #d4c08a;
  --panel-rgb: 24, 48, 38; --hero-rgb: 32, 62, 50; --ink-rgb: 6, 16, 12; --pop-rgb: 22, 44, 35;
  --pink-rgb: 111, 207, 168; --cyan-rgb: 111, 195, 192; --violet-rgb: 168, 197, 181;
  --green-rgb: 143, 224, 181; --amber-rgb: 212, 192, 138;
  --text-main: #e6f2ec; --surface-active: #3f7c62;
  --tx-strong: #d2e8dd; --tx-soft: #a4c4b4; --tx-dim: #87a997; --tx-faint: #6a8a79;
  --tx-mute: #4e6a5c; --amber-mute: #a89a72;
  --line-rgb: 70, 105, 88; --veil-rgb: 4, 10, 8;
  --bar-track: #1d382d; --bar-tip: #356350; --apply-ink: #0e2018;
  --heat-1: #2e5c48; --heat-2: #4f9070; --heat-3: #7fc9a5; --heat-4: #a9e0c4; --heat-5: #d8f3e5;
}
/* jade keycaps: polished gem sheen + engraved dark glyphs */
html[data-theme="jade"] .keycap {
  background:
    radial-gradient(130% 90% at 30% 18%, rgba(255, 255, 255, .32), rgba(255, 255, 255, 0) 46%),
    linear-gradient(165deg, #a8ddc0, #67ab8c 55%, #47806a);
  border-color: rgba(20, 60, 45, .35);
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, .4), inset 0 -2px 4px rgba(20, 70, 50, .28), 0 4px 10px rgba(10, 30, 22, .45);
}
html[data-theme="jade"] .keycap span,
html[data-theme="jade"] .keycap b { color: rgba(18, 58, 42, .92); }
html[data-theme="jade"] .keycap.muted { opacity: .5; }

/* wood 原木 — warm walnut with visible grain on every key */
html[data-theme="wood"] {
  --page-bg: #221812; --page-glow: rgba(216, 160, 100, .15);
  --acc-pink: #d89b5f; --acc-pink-bright: #c9884a; --acc-pink-soft: #e6b98a;
  --acc-cyan: #b8a184; --acc-cyan-bright: #a68f72;
  --acc-violet: #b59a85; --acc-green: #a3a06c; --acc-amber: #e0b878;
  --panel-rgb: 48, 34, 24; --hero-rgb: 64, 46, 32; --ink-rgb: 16, 10, 6; --pop-rgb: 44, 31, 22;
  --pink-rgb: 216, 155, 95; --cyan-rgb: 184, 161, 132; --violet-rgb: 181, 154, 133;
  --green-rgb: 163, 160, 108; --amber-rgb: 224, 184, 120;
  --text-main: #f2e8dc; --surface-active: #7a5a38;
  --tx-strong: #e6d5c0; --tx-soft: #c0a88e; --tx-dim: #a08a72; --tx-faint: #7e6c58;
  --tx-mute: #5e4f3e; --amber-mute: #b09568;
  --line-rgb: 105, 82, 60; --veil-rgb: 10, 6, 4;
  --bar-track: #3a2a1c; --bar-tip: #644831; --apply-ink: #2a1a0e;
  --heat-1: #5c4028; --heat-2: #8a6238; --heat-3: #c08c4e; --heat-4: #dfb878; --heat-5: #f2dcae;
}
/* wood keycaps: fine grain stripes over honey walnut */
html[data-theme="wood"] .keycap {
  background:
    repeating-linear-gradient(93deg, rgba(70, 40, 16, .18) 0 1.5px, rgba(255, 236, 205, .07) 1.5px 3px, rgba(70, 40, 16, .10) 3px 4.5px, transparent 4.5px 7px),
    linear-gradient(172deg, #dcae74, #bd8a52 58%, #a06c3e);
  border-color: rgba(58, 34, 14, .45);
  box-shadow: inset 0 1px 1px rgba(255, 230, 190, .35), 0 4px 10px rgba(10, 5, 2, .5);
}
html[data-theme="wood"] .keycap span,
html[data-theme="wood"] .keycap b { color: rgba(58, 34, 14, .92); }
html[data-theme="wood"] .keycap.muted { opacity: .5; }

""" + anchor
t = t.replace(anchor, themes, 1)

# register in options + group order
old = """  { id: "pine", name: "松涛夜", group: "温和纸感", dots: ["#7fb59a", "#6fa8a8", "#c4b083"] },"""
new = """  { id: "pine", name: "松涛夜", group: "温和纸感", dots: ["#7fb59a", "#6fa8a8", "#c4b083"] },
  { id: "jade", name: "玉石", group: "材质质感", dots: ["#7fc9a5", "#6fc3c0", "#d4c08a"] },
  { id: "wood", name: "原木", group: "材质质感", dots: ["#d89b5f", "#b8a184", "#e0b878"] },"""
assert old in t
t = t.replace(old, new)

old_order = 'const themeGroupOrder = ["温和纸感", "苹果质感", "高饱和霓虹"];'
new_order = 'const themeGroupOrder = ["材质质感", "温和纸感", "苹果质感", "高饱和霓虹"];'
assert old_order in t
t = t.replace(old_order, new_order)
p.write_text(t, encoding="utf-8")
print("jade + wood material themes added")
