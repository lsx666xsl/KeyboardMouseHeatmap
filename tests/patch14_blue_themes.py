"""Add two gentle blue themes: mist-blue (light paper) and indigo-night (soft dark)."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

anchor = "/* latte 拿铁暖白 — warm paper-light, caramel & cream (calm, low glare) */"
assert anchor in t

themes = """
/* mist-blue 雾蓝 — light paper blue, calm as a hazy morning sky */
html[data-theme="mist-blue"] {
  color-scheme: light;
  --page-bg: #eef3f7; --page-glow: rgba(96, 145, 185, .13);
  --acc-pink: #6d9bc3; --acc-pink-bright: #5586b0; --acc-pink-soft: #8bb3d1;
  --acc-cyan: #6fa3b8; --acc-cyan-bright: #5b93aa;
  --acc-violet: #94a3c7; --acc-green: #7aa892; --acc-amber: #c2a878;
  --panel-rgb: 252, 254, 255; --hero-rgb: 240, 246, 251; --ink-rgb: 229, 237, 243; --pop-rgb: 248, 251, 253;
  --pink-rgb: 109, 155, 195; --cyan-rgb: 111, 163, 184; --violet-rgb: 148, 163, 199;
  --green-rgb: 122, 168, 146; --amber-rgb: 194, 168, 120;
  --text-main: #2b3a47; --surface-active: #ccdbe6;
  --tx-strong: #46586a; --tx-soft: #6d8093; --tx-dim: #8698a9; --tx-faint: #a3b3c2;
  --tx-mute: #bcc9d4; --amber-mute: #93805c;
  --line-rgb: 205, 218, 228; --veil-rgb: 238, 243, 247;
  --bar-track: #dfe8ef; --bar-tip: #c2d2de; --apply-ink: #ffffff;
  --heat-1: #c9dcea; --heat-2: #9cc3dc; --heat-3: #6d9bc3; --heat-4: #4f7ea8; --heat-5: #33587a;
}
/* indigo-night 靛夜 — soft low-saturation indigo dark, gentle on the eyes */
html[data-theme="indigo-night"] {
  --page-bg: #1b2233; --page-glow: rgba(122, 150, 199, .15);
  --acc-pink: #7d9ecb; --acc-pink-bright: #93b1d8; --acc-pink-soft: #a9c4e3;
  --acc-cyan: #79a8c0; --acc-cyan-bright: #8fbacd;
  --acc-violet: #9a94c9; --acc-green: #83ad9b; --acc-amber: #c9b489;
  --panel-rgb: 30, 38, 57; --hero-rgb: 41, 52, 77; --ink-rgb: 14, 18, 28; --pop-rgb: 27, 34, 52;
  --pink-rgb: 125, 158, 203; --cyan-rgb: 121, 168, 192; --violet-rgb: 154, 148, 201;
  --green-rgb: 131, 173, 155; --amber-rgb: 201, 180, 137;
  --text-main: #e8edf5; --surface-active: #45557a;
  --tx-strong: #d5dde9; --tx-soft: #a6b2c5; --tx-dim: #8996ab; --tx-faint: #6c7889;
  --tx-mute: #525c6e; --amber-mute: #a08c69;
  --line-rgb: 84, 96, 118; --veil-rgb: 8, 11, 17;
  --bar-track: #2b3550; --bar-tip: #48587e; --apply-ink: #ffffff;
  --heat-1: #33405c; --heat-2: #5f7ba6; --heat-3: #7d9ecb; --heat-4: #a8b9d8; --heat-5: #cfdcec;
}
"""

t = t.replace(anchor, themes + anchor)
p.write_text(t, encoding="utf-8")
print("2 blue themes injected")
