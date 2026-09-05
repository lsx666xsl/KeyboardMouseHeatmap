"""Add 3 gentle blue/green themes: celadon, lakeside, pine-night."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

anchor = "/* lavender 薰衣草 — soft powdery purple on pale paper */"
assert anchor in t

themes = """
/* celadon 青瓷 — porcelain green-blue, quiet and smooth */
html[data-theme="celadon"] {
  color-scheme: light;
  --page-bg: #eff4f1; --page-glow: rgba(111, 170, 149, .13);
  --acc-pink: #6faa95; --acc-pink-bright: #59967f; --acc-pink-soft: #93c2af;
  --acc-cyan: #7ba6b8; --acc-cyan-bright: #6893a8;
  --acc-violet: #9aa8b8; --acc-green: #6aa583; --acc-amber: #c2a878;
  --panel-rgb: 251, 253, 252; --hero-rgb: 240, 246, 243; --ink-rgb: 230, 238, 234; --pop-rgb: 248, 251, 250;
  --pink-rgb: 111, 170, 149; --cyan-rgb: 123, 166, 184; --violet-rgb: 154, 168, 184;
  --green-rgb: 106, 165, 131; --amber-rgb: 194, 168, 120;
  --text-main: #2c3a34; --surface-active: #ccdfd5;
  --tx-strong: #45564d; --tx-soft: #6a7d72; --tx-dim: #839689; --tx-faint: #9fb0a5;
  --tx-mute: #b9c8be; --amber-mute: #93805c;
  --line-rgb: 209, 222, 214; --veil-rgb: 239, 244, 241;
  --bar-track: #dee9e2; --bar-tip: #c1d3c8; --apply-ink: #ffffff;
  --heat-1: #d3e4da; --heat-2: #a3c8b4; --heat-3: #6faa95; --heat-4: #528871; --heat-5: #34604c;
}
/* lakeside 湖畔 — clear lake teal, light and breezy */
html[data-theme="lakeside"] {
  color-scheme: light;
  --page-bg: #ecf3f4; --page-glow: rgba(93, 163, 168, .14);
  --acc-pink: #5da3a8; --acc-pink-bright: #4b8f95; --acc-pink-soft: #86bfc3;
  --acc-cyan: #64a9c4; --acc-cyan-bright: #5498b4;
  --acc-violet: #93a3c0; --acc-green: #74ad8f; --acc-amber: #c6ad80;
  --panel-rgb: 251, 253, 254; --hero-rgb: 239, 246, 247; --ink-rgb: 228, 237, 238; --pop-rgb: 248, 252, 252;
  --pink-rgb: 93, 163, 168; --cyan-rgb: 100, 169, 196; --violet-rgb: 147, 163, 192;
  --green-rgb: 116, 173, 143; --amber-rgb: 198, 173, 128;
  --text-main: #26393c; --surface-active: #c9dde0;
  --tx-strong: #3d5356; --tx-soft: #62777b; --tx-dim: #7c9094; --tx-faint: #98a9ad;
  --tx-mute: #b2c2c5; --amber-mute: #93805e;
  --line-rgb: 206, 221, 223; --veil-rgb: 236, 243, 244;
  --bar-track: #dbe8e9; --bar-tip: #bed2d4; --apply-ink: #ffffff;
  --heat-1: #d2e6e6; --heat-2: #9cc9cb; --heat-3: #5da3a8; --heat-4: #45838a; --heat-5: #2b5c63;
}
/* pine 松涛夜 — deep forest green night, dark but soft */
html[data-theme="pine"] {
  --page-bg: #131e19; --page-glow: rgba(127, 181, 154, .14);
  --acc-pink: #7fb59a; --acc-pink-bright: #95c5ac; --acc-pink-soft: #aed4c1;
  --acc-cyan: #6fa8a8; --acc-cyan-bright: #85babd;
  --acc-violet: #96a3b5; --acc-green: #6fb389; --acc-amber: #c4b083;
  --panel-rgb: 24, 36, 30; --hero-rgb: 33, 50, 41; --ink-rgb: 8, 14, 11; --pop-rgb: 21, 32, 26;
  --pink-rgb: 127, 181, 154; --cyan-rgb: 111, 168, 168; --violet-rgb: 150, 163, 181;
  --green-rgb: 111, 179, 137; --amber-rgb: 196, 176, 131;
  --text-main: #e6efe9; --surface-active: #3c5a4b;
  --tx-strong: #d3e2d8; --tx-soft: #a3b6aa; --tx-dim: #86998d; --tx-faint: #697c70;
  --tx-mute: #4e6055; --amber-mute: #9c8a66;
  --line-rgb: 78, 96, 85; --veil-rgb: 5, 9, 7;
  --bar-track: #24382e; --bar-tip: #40604f; --apply-ink: #ffffff;
  --heat-1: #2c4438; --heat-2: #4a7360; --heat-3: #7fb59a; --heat-4: #a8ccb8; --heat-5: #d5e8dd;
}
"""

t = t.replace(anchor, themes + anchor)
p.write_text(t, encoding="utf-8")
print("3 blue/green themes injected")
