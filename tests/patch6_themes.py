"""Add 6 saturated designer-inspired themes to the global style block."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

anchor = "/* graphite 石墨 — clean dark, Apple-like neutral surfaces with vivid accents */"
assert anchor in t

themes = '''
/* neon-drive 霓虹夜驰 — classic synthwave (designer palette: #FF2FD4 #05F4FF #0B032D) */
html[data-theme="neon-drive"] {
  --page-bg: #0b032d; --page-glow: rgba(5, 244, 255, .2);
  --acc-pink: #ff2fd4; --acc-pink-bright: #ff6fe0; --acc-pink-soft: #ffa4ec;
  --acc-cyan: #05f4ff; --acc-cyan-bright: #55faff;
  --acc-violet: #7b2cff; --acc-green: #f9f871; --acc-amber: #ffb86b;
  --panel-rgb: 18, 5, 52; --hero-rgb: 28, 8, 78; --ink-rgb: 5, 1, 20; --pop-rgb: 22, 6, 60;
  --pink-rgb: 255, 47, 212; --cyan-rgb: 5, 244, 255; --violet-rgb: 123, 44, 255;
  --green-rgb: 249, 248, 113; --amber-rgb: 255, 184, 107;
  --surface-active: #40138f; --bar-track: #1d0a44; --bar-tip: #4b1ea0; --apply-ink: #0b032d;
  --heat-1: #2b2dff; --heat-2: #05f4ff; --heat-3: #ff2fd4; --heat-4: #ffb86b; --heat-5: #f9f871;
}
/* miami 迈阿密海岸 — Miami Vice coastal neon (designer palette: #FF5E9F #3AE7FF #0B1021) */
html[data-theme="miami"] {
  --page-bg: #0b1021; --page-glow: rgba(58, 231, 255, .18);
  --acc-pink: #ff5e9f; --acc-pink-bright: #ff82b9; --acc-pink-soft: #ffa8d0;
  --acc-cyan: #3ae7ff; --acc-cyan-bright: #7cf1ff;
  --acc-violet: #1f2cff; --acc-green: #09fbd3; --acc-amber: #ffb86b;
  --panel-rgb: 16, 22, 48; --hero-rgb: 24, 34, 72; --ink-rgb: 4, 6, 16; --pop-rgb: 20, 26, 58;
  --pink-rgb: 255, 94, 159; --cyan-rgb: 58, 231, 255; --violet-rgb: 31, 44, 255;
  --green-rgb: 9, 251, 211; --amber-rgb: 255, 184, 107;
  --surface-active: #2739a8; --bar-track: #182648; --bar-tip: #3a52c8; --apply-ink: #0b1021;
  --heat-1: #2b3a8f; --heat-2: #3ae7ff; --heat-3: #09fbd3; --heat-4: #ffb86b; --heat-5: #ff5e9f;
}
/* sunset-horizon 落日地平线 — synthwave sun gradient (designer: #FF006E #7B2CFF #240046) */
html[data-theme="sunset-horizon"] {
  --page-bg: #240046; --page-glow: rgba(255, 0, 110, .26);
  --acc-pink: #ff006e; --acc-pink-bright: #ff4d94; --acc-pink-soft: #ff85b8;
  --acc-cyan: #9d4edd; --acc-cyan-bright: #bf77ea;
  --acc-violet: #7b2cff; --acc-green: #ffd670; --acc-amber: #ffbf69;
  --panel-rgb: 40, 0, 70; --hero-rgb: 58, 4, 100; --ink-rgb: 12, 0, 24; --pop-rgb: 34, 2, 60;
  --pink-rgb: 255, 0, 110; --cyan-rgb: 157, 78, 221; --violet-rgb: 123, 44, 255;
  --green-rgb: 255, 214, 112; --amber-rgb: 255, 191, 105;
  --surface-active: #6a1fb0; --bar-track: #33064f; --bar-tip: #6b239e; --apply-ink: #240046;
  --heat-1: #4a0e8f; --heat-2: #7b2cff; --heat-3: #ff006e; --heat-4: #ff5c39; --heat-5: #ffd670;
}
/* laser-horizon 镭射地平线 — laser streaks over violet night (designer: #FF3F8E #FF8A3D #1A0B2E) */
html[data-theme="laser-horizon"] {
  --page-bg: #1a0b2e; --page-glow: rgba(255, 63, 142, .24);
  --acc-pink: #ff3f8e; --acc-pink-bright: #ff6fac; --acc-pink-soft: #ff9fcb;
  --acc-cyan: #ff8a3d; --acc-cyan-bright: #ffab6f;
  --acc-violet: #7b2cff; --acc-green: #4dffc3; --acc-amber: #ffd447;
  --panel-rgb: 32, 14, 60; --hero-rgb: 46, 20, 88; --ink-rgb: 10, 3, 20; --pop-rgb: 30, 12, 56;
  --pink-rgb: 255, 63, 142; --cyan-rgb: 255, 138, 61; --violet-rgb: 123, 44, 255;
  --green-rgb: 77, 255, 195; --amber-rgb: 255, 212, 71;
  --surface-active: #6420b8; --bar-track: #2c1454; --bar-tip: #5a2aa0; --apply-ink: #1a0b2e;
  --heat-1: #3d1680; --heat-2: #7b2cff; --heat-3: #ff3f8e; --heat-4: #ff8a3d; --heat-5: #ffd447;
}
/* cyber-alley 赛博雨巷 — rainy neon city (designer: #08F7FE #FE53BB #050816) */
html[data-theme="cyber-alley"] {
  --page-bg: #050816; --page-glow: rgba(8, 247, 254, .2);
  --acc-pink: #fe53bb; --acc-pink-bright: #ff7fd0; --acc-pink-soft: #ffa9e0;
  --acc-cyan: #08f7fe; --acc-cyan-bright: #70fbff;
  --acc-violet: #7c83ff; --acc-green: #09fbd3; --acc-amber: #f5d300;
  --panel-rgb: 10, 14, 40; --hero-rgb: 16, 22, 60; --ink-rgb: 2, 4, 12; --pop-rgb: 12, 16, 46;
  --pink-rgb: 254, 83, 187; --cyan-rgb: 8, 247, 254; --violet-rgb: 124, 131, 255;
  --green-rgb: 9, 251, 211; --amber-rgb: 245, 211, 0;
  --surface-active: #1f3f9e; --bar-track: #131a44; --bar-tip: #2f48a8; --apply-ink: #050816;
  --heat-1: #121c66; --heat-2: #08f7fe; --heat-3: #fe53bb; --heat-4: #f5d300; --heat-5: #09fbd3;
}
/* volt 荧光青柠 — acid lime on deep green-black */
html[data-theme="volt"] {
  --page-bg: #0c1400; --page-glow: rgba(204, 255, 0, .2);
  --acc-pink: #ccff00; --acc-pink-bright: #dbff57; --acc-pink-soft: #eaff9e;
  --acc-cyan: #00ff9d; --acc-cyan-bright: #52ffbb;
  --acc-violet: #00e5ff; --acc-green: #a8ff3e; --acc-amber: #ffee32;
  --panel-rgb: 18, 32, 6; --hero-rgb: 28, 48, 10; --ink-rgb: 4, 10, 2; --pop-rgb: 16, 28, 6;
  --pink-rgb: 204, 255, 0; --cyan-rgb: 0, 255, 157; --violet-rgb: 0, 229, 255;
  --green-rgb: 168, 255, 62; --amber-rgb: 255, 238, 50;
  --surface-active: #2f5c1a; --bar-track: #12260c; --bar-tip: #2b4f1a; --apply-ink: #0c1400;
  --heat-1: #005c2e; --heat-2: #00ff9d; --heat-3: #ccff00; --heat-4: #ffee32; --heat-5: #ff9e00;
}
'''

t = t.replace(anchor, themes + anchor)
p.write_text(t, encoding="utf-8")
print("6 themes injected")
