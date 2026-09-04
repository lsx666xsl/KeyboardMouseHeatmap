"""Add 5 calm designer themes (paper/earthy/morandi) to the global style."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

anchor = "/* graphite 石墨 — clean dark, Apple-like neutral surfaces with vivid accents */"
assert anchor in t

themes = """
/* latte 拿铁暖白 — warm paper-light, caramel & cream (calm, low glare) */
html[data-theme="latte"] {
  color-scheme: light;
  --page-bg: #f6f0e4; --page-glow: rgba(192, 148, 110, .14);
  --acc-pink: #b98a5e; --acc-pink-bright: #a5713f; --acc-pink-soft: #caa377;
  --acc-cyan: #7f97a5; --acc-cyan-bright: #6c8b9c;
  --acc-violet: #a590a8; --acc-green: #7ba080; --acc-amber: #c9a05f;
  --panel-rgb: 255, 252, 246; --hero-rgb: 248, 242, 232; --ink-rgb: 240, 233, 221; --pop-rgb: 252, 248, 240;
  --pink-rgb: 185, 138, 94; --cyan-rgb: 127, 151, 165; --violet-rgb: 165, 144, 168;
  --green-rgb: 123, 160, 128; --amber-rgb: 201, 160, 95;
  --text-main: #37322a; --surface-active: #d9cdb6;
  --tx-strong: #54493c; --tx-soft: #7d7162; --tx-dim: #94897a; --tx-faint: #b0a695;
  --tx-mute: #c6bca9; --amber-mute: #9c7f52;
  --line-rgb: 214, 204, 188; --veil-rgb: 245, 240, 230;
  --bar-track: #e4dccb; --bar-tip: #cbbfa6; --apply-ink: #ffffff;
  --heat-1: #d9c8a8; --heat-2: #c9a882; --heat-3: #b98a5e; --heat-4: #a5713f; --heat-5: #7a4f2c;
}
/* sage 鼠尾草绿 — soft sage on cool paper */
html[data-theme="sage"] {
  color-scheme: light;
  --page-bg: #eef2ea; --page-glow: rgba(123, 168, 137, .16);
  --acc-pink: #7ba889; --acc-pink-bright: #5f8f6e; --acc-pink-soft: #93bda0;
  --acc-cyan: #7ea3b0; --acc-cyan-bright: #6b92a1;
  --acc-violet: #9b92b5; --acc-green: #6f9a74; --acc-amber: #c7a25f;
  --panel-rgb: 252, 255, 250; --hero-rgb: 244, 248, 240; --ink-rgb: 234, 240, 230; --pop-rgb: 248, 251, 246;
  --pink-rgb: 123, 168, 137; --cyan-rgb: 126, 163, 176; --violet-rgb: 155, 146, 181;
  --green-rgb: 111, 154, 116; --amber-rgb: 199, 162, 95;
  --text-main: #2f352e; --surface-active: #d4dfd0;
  --tx-strong: #4b5647; --tx-soft: #6f7d6d; --tx-dim: #88968a; --tx-faint: #a3b0a5;
  --tx-mute: #b9c3b8; --amber-mute: #8f7647;
  --line-rgb: 210, 218, 206; --veil-rgb: 240, 245, 238;
  --bar-track: #dfe6db; --bar-tip: #c2cfc0; --apply-ink: #ffffff;
  --heat-1: #d5e3d4; --heat-2: #a9c4ae; --heat-3: #7ba889; --heat-4: #5f8f6e; --heat-5: #3f6049;
}
/* matcha 抹茶和纸 — washi paper with matcha green */
html[data-theme="matcha"] {
  color-scheme: light;
  --page-bg: #f4f0e2; --page-glow: rgba(138, 154, 91, .15);
  --acc-pink: #8a9a5b; --acc-pink-bright: #71824a; --acc-pink-soft: #a3b177;
  --acc-cyan: #7e9a8b; --acc-cyan-bright: #6b8978;
  --acc-violet: #a6969f; --acc-green: #95a567; --acc-amber: #d0a259;
  --panel-rgb: 253, 250, 242; --hero-rgb: 245, 241, 230; --ink-rgb: 236, 231, 218; --pop-rgb: 249, 245, 236;
  --pink-rgb: 138, 154, 91; --cyan-rgb: 126, 154, 139; --violet-rgb: 166, 150, 159;
  --green-rgb: 149, 165, 103; --amber-rgb: 208, 162, 89;
  --text-main: #36362c; --surface-active: #dcd5bc;
  --tx-strong: #4d4d3e; --tx-soft: #74745f; --tx-dim: #8d8c76; --tx-faint: #a8a692;
  --tx-mute: #bfbda9; --amber-mute: #93713a;
  --line-rgb: 214, 210, 190; --veil-rgb: 244, 240, 228;
  --bar-track: #e3ddc9; --bar-tip: #c9c1a4; --apply-ink: #ffffff;
  --heat-1: #dcd8b6; --heat-2: #b9bd7f; --heat-3: #8a9a5b; --heat-4: #71824a; --heat-5: #4d5c31;
}
/* dusk 暮云蓝 — calm misty blue-grey (dark, low glare) */
html[data-theme="dusk"] {
  --page-bg: #222936; --page-glow: rgba(140, 168, 201, .14);
  --acc-pink: #8fa8c9; --acc-pink-bright: #7697bd; --acc-pink-soft: #aec2db;
  --acc-cyan: #7fb2c4; --acc-cyan-bright: #6fa3b6;
  --acc-violet: #a191c4; --acc-green: #86b39a; --acc-amber: #c9b283;
  --panel-rgb: 34, 42, 58; --hero-rgb: 46, 56, 76; --ink-rgb: 16, 21, 30; --pop-rgb: 30, 38, 54;
  --pink-rgb: 143, 168, 201; --cyan-rgb: 127, 178, 196; --violet-rgb: 161, 145, 196;
  --green-rgb: 134, 179, 154; --amber-rgb: 201, 178, 131;
  --text-main: #eceff4; --surface-active: #4a5a7a;
  --tx-strong: #d8dee8; --tx-soft: #a9b2c2; --tx-dim: #8c96a8; --tx-faint: #6e7889;
  --tx-mute: #545d6d; --amber-mute: #a6906a;
  --line-rgb: 86, 96, 116; --veil-rgb: 10, 13, 18;
  --bar-track: #303c54; --bar-tip: #4d5d7e; --apply-ink: #ffffff;
  --heat-1: #33405c; --heat-2: #6d8cad; --heat-3: #a3bad6; --heat-4: #d4c59e; --heat-5: #b58a6e;
}
/* cocoa 可可陶土 — dark cocoa with terracotta & sand */
html[data-theme="cocoa"] {
  --page-bg: #282019; --page-glow: rgba(201, 141, 109, .15);
  --acc-pink: #c98d6d; --acc-pink-bright: #b37758; --acc-pink-soft: #d8a587;
  --acc-cyan: #a89a86; --acc-cyan-bright: #968a76;
  --acc-violet: #ad90a0; --acc-green: #a3a06c; --acc-amber: #d9b37a;
  --panel-rgb: 46, 36, 28; --hero-rgb: 60, 48, 38; --ink-rgb: 20, 15, 11; --pop-rgb: 42, 32, 25;
  --pink-rgb: 201, 141, 109; --cyan-rgb: 168, 154, 134; --violet-rgb: 173, 144, 160;
  --green-rgb: 163, 160, 108; --amber-rgb: 217, 179, 122;
  --text-main: #f1eae2; --surface-active: #6e5540;
  --tx-strong: #ddd1c4; --tx-soft: #ab9d8d; --tx-dim: #8e8070; --tx-faint: #6f6355;
  --tx-mute: #564c40; --amber-mute: #a3875c;
  --line-rgb: 96, 84, 72; --veil-rgb: 12, 9, 7;
  --bar-track: #443629; --bar-tip: #6d5843; --apply-ink: #ffffff;
  --heat-1: #5c4230; --heat-2: #8a5f43; --heat-3: #c98d6d; --heat-4: #d9b37a; --heat-5: #ecd9b2;
}
"""

t = t.replace(anchor, themes + anchor)
p.write_text(t, encoding="utf-8")
print("5 calm themes injected")
