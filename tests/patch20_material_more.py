"""Add material themes: brushed metal, marble, frosted glass."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

anchor = "/* jade 玉石 — polished translucent green stone with gem sheen */"
assert anchor in t

themes = """
/* metal 金属拉丝 — brushed steel with fine diagonal grain */
html[data-theme="metal"] {
  --page-bg: #1a1d22; --page-glow: rgba(160, 180, 200, .14);
  --acc-pink: #aeb9c6; --acc-pink-bright: #c3cdd8; --acc-pink-soft: #d8e0e8;
  --acc-cyan: #8fb6cf; --acc-cyan-bright: #aac9de;
  --acc-violet: #9aa4c0; --acc-green: #96c2a4; --acc-amber: #d9b878;
  --panel-rgb: 28, 32, 39; --hero-rgb: 38, 44, 53; --ink-rgb: 10, 12, 16; --pop-rgb: 25, 29, 36;
  --pink-rgb: 174, 185, 198; --cyan-rgb: 143, 182, 207; --violet-rgb: 154, 164, 192;
  --green-rgb: 150, 194, 164; --amber-rgb: 217, 184, 120;
  --text-main: #e8ecf1; --surface-active: #47525f;
  --tx-strong: #d5dde5; --tx-soft: #a6b1bd; --tx-dim: #8995a2; --tx-faint: #6b7683;
  --tx-mute: #4d5763; --amber-mute: #a89268;
  --line-rgb: 74, 82, 92; --veil-rgb: 5, 7, 9;
  --bar-track: #262c34; --bar-tip: #434d59; --apply-ink: #10141a;
  --heat-1: #3a424e; --heat-2: #5f6c7c; --heat-3: #8d9aa9; --heat-4: #b8c4d1; --heat-5: #e2e9f0;
}
html[data-theme="metal"] .keycap {
  background:
    repeating-linear-gradient(65deg, rgba(255, 255, 255, .10) 0 1px, rgba(18, 24, 32, .20) 1px 2.5px, transparent 2.5px 4px),
    linear-gradient(160deg, #cdd7e1, #8d99a8 55%, #616d7c);
  border-color: rgba(28, 36, 46, .5);
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, .45), inset 0 -2px 4px rgba(18, 24, 32, .3), 0 4px 10px rgba(5, 8, 12, .5);
}
html[data-theme="metal"] .keycap span,
html[data-theme="metal"] .keycap b { color: rgba(26, 34, 44, .92); }
html[data-theme="metal"] .keycap.muted { opacity: .5; }

/* marble 大理石 — warm white stone with grey-gold veins */
html[data-theme="marble"] {
  color-scheme: light;
  --page-bg: #f2f1ee; --page-glow: rgba(138, 151, 168, .13);
  --acc-pink: #8a97a8; --acc-pink-bright: #77879a; --acc-pink-soft: #a5b2c2;
  --acc-cyan: #7fa8b8; --acc-cyan-bright: #6d97a9;
  --acc-violet: #a89bb8; --acc-green: #8fa892; --acc-amber: #c9b478;
  --panel-rgb: 253, 253, 251; --hero-rgb: 243, 242, 238; --ink-rgb: 235, 234, 229; --pop-rgb: 250, 250, 247;
  --pink-rgb: 138, 151, 168; --cyan-rgb: 127, 168, 184; --violet-rgb: 168, 155, 184;
  --green-rgb: 143, 168, 146; --amber-rgb: 201, 180, 120;
  --text-main: #33393f; --surface-active: #d8d9d4;
  --tx-strong: #4a5058; --tx-soft: #6d747d; --tx-dim: #858c95; --tx-faint: #a0a6ad;
  --tx-mute: #b9bec4; --amber-mute: #96825a;
  --line-rgb: 216, 216, 210; --veil-rgb: 242, 241, 238;
  --bar-track: #e4e3de; --bar-tip: #c8c7c0; --apply-ink: #ffffff;
  --heat-1: #d6d9de; --heat-2: #adb6c2; --heat-3: #8a97a8; --heat-4: #a8926a; --heat-5: #c9a45e;
}
html[data-theme="marble"] .keycap {
  background:
    radial-gradient(60% 45% at 72% 28%, rgba(120, 135, 155, .20), transparent 60%),
    radial-gradient(50% 40% at 25% 72%, rgba(120, 135, 155, .15), transparent 55%),
    linear-gradient(64deg, transparent 45%, rgba(110, 125, 145, .35) 47%, rgba(110, 125, 145, .10) 49%, transparent 53%),
    linear-gradient(118deg, transparent 58%, rgba(170, 150, 110, .28) 60%, transparent 64%),
    linear-gradient(170deg, #fdfdfb, #ecebe5);
  border-color: rgba(90, 100, 115, .32);
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, .85), 0 4px 10px rgba(40, 50, 65, .22);
}
html[data-theme="marble"] .keycap span,
html[data-theme="marble"] .keycap b { color: rgba(55, 65, 80, .9); }
html[data-theme="marble"] .keycap.muted { opacity: .5; }

/* frost 磨砂玻璃 — translucent icy caps over aurora glow */
html[data-theme="frost"] {
  --page-bg: #0d1424; --page-glow: rgba(120, 170, 255, .22);
  --acc-pink: #8fc7f0; --acc-pink-bright: #aad8f7; --acc-pink-soft: #c4e4fb;
  --acc-cyan: #7fd4e8; --acc-cyan-bright: #9ce1f0;
  --acc-violet: #a99fe8; --acc-green: #8fe0c0; --acc-amber: #f0d098;
  --panel-rgb: 20, 30, 52; --hero-rgb: 28, 42, 72; --ink-rgb: 6, 10, 20; --pop-rgb: 18, 28, 48;
  --pink-rgb: 143, 199, 240; --cyan-rgb: 127, 212, 232; --violet-rgb: 169, 159, 232;
  --green-rgb: 143, 224, 192; --amber-rgb: 240, 208, 152;
  --text-main: #eaf3ff; --surface-active: #33507e;
  --tx-strong: #d5e4f7; --tx-soft: #a3b7d1; --tx-dim: #8496b2; --tx-faint: #66788f;
  --tx-mute: #495a75; --amber-mute: #b09a72;
  --line-rgb: 72, 90, 120; --veil-rgb: 4, 7, 14;
  --bar-track: #1c2b47; --bar-tip: #33507e; --apply-ink: #0d1424;
  --heat-1: #2c3e60; --heat-2: #4f6f9e; --heat-3: #8fc7f0; --heat-4: #a9c8f5; --heat-5: #d5ebff;
}
html[data-theme="frost"] .keycap {
  background:
    linear-gradient(120deg, rgba(255, 255, 255, .18), rgba(255, 255, 255, .04) 55%),
    linear-gradient(180deg, rgba(143, 199, 240, .26), rgba(169, 159, 232, .18));
  border-color: rgba(255, 255, 255, .28);
  backdrop-filter: blur(6px);
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, .4), 0 4px 12px rgba(20, 40, 80, .4);
}
html[data-theme="frost"] .keycap span,
html[data-theme="frost"] .keycap b { color: rgba(234, 243, 255, .95); }
html[data-theme="frost"] .keycap.muted { opacity: .5; }

""" + anchor
t = t.replace(anchor, themes, 1)

old = """  { id: "wood", name: "原木", group: "材质质感", dots: ["#d89b5f", "#b8a184", "#e0b878"] },"""
new = """  { id: "wood", name: "原木", group: "材质质感", dots: ["#d89b5f", "#b8a184", "#e0b878"] },
  { id: "metal", name: "金属拉丝", group: "材质质感", dots: ["#aeb9c6", "#8fb6cf", "#d9b878"] },
  { id: "marble", name: "大理石", group: "材质质感", dots: ["#8a97a8", "#c9b478", "#7fa8b8"] },
  { id: "frost", name: "磨砂玻璃", group: "材质质感", dots: ["#8fc7f0", "#a99fe8", "#8fe0c0"] },"""
assert old in t
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("metal + marble + frost material themes added")
