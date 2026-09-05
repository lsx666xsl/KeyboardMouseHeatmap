"""Add 4 more gentle paper themes: lavender, sakura, peach, mint."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

anchor = "/* latte 拿铁暖白 — warm paper-light, caramel & cream (calm, low glare) */"
assert anchor in t

themes = """
/* lavender 薰衣草 — soft powdery purple on pale paper */
html[data-theme="lavender"] {
  color-scheme: light;
  --page-bg: #f3f0f7; --page-glow: rgba(155, 140, 196, .13);
  --acc-pink: #9b8cc4; --acc-pink-bright: #8778b3; --acc-pink-soft: #b0a4d4;
  --acc-cyan: #8ba3bd; --acc-cyan-bright: #7a94b0;
  --acc-violet: #a58fc0; --acc-green: #8aa892; --acc-amber: #c7ab7e;
  --panel-rgb: 253, 251, 255; --hero-rgb: 244, 241, 249; --ink-rgb: 234, 230, 242; --pop-rgb: 250, 248, 253;
  --pink-rgb: 155, 140, 196; --cyan-rgb: 139, 163, 189; --violet-rgb: 165, 143, 192;
  --green-rgb: 138, 168, 146; --amber-rgb: 199, 171, 126;
  --text-main: #343042; --surface-active: #d8d2e6;
  --tx-strong: #4f4a63; --tx-soft: #75708a; --tx-dim: #8d89a1; --tx-faint: #a7a3b9;
  --tx-mute: #c0bdcf; --amber-mute: #96835d;
  --line-rgb: 216, 212, 228; --veil-rgb: 243, 240, 247;
  --bar-track: #e5e1ee; --bar-tip: #ccc6dc; --apply-ink: #ffffff;
  --heat-1: #dcd6ea; --heat-2: #b3a6d4; --heat-3: #9b8cc4; --heat-4: #7768a3; --heat-5: #544878;
}
/* sakura 樱花三月 — dusty rose on warm blossom paper */
html[data-theme="sakura"] {
  color-scheme: light;
  --page-bg: #f9f0f2; --page-glow: rgba(214, 141, 162, .14);
  --acc-pink: #d68da2; --acc-pink-bright: #c4748d; --acc-pink-soft: #e2aabb;
  --acc-cyan: #96aec0; --acc-cyan-bright: #849e b2;
  --acc-violet: #b493bb; --acc-green: #93ad8f; --acc-amber: #d3b183;
  --panel-rgb: 255, 251, 252; --hero-rgb: 250, 241, 244; --ink-rgb: 243, 231, 235; --pop-rgb: 253, 247, 249;
  --pink-rgb: 214, 141, 162; --cyan-rgb: 150, 174, 192; --violet-rgb: 180, 147, 187;
  --green-rgb: 147, 173, 143; --amber-rgb: 211, 177, 131;
  --text-main: #42333a; --surface-active: #ecd3da;
  --tx-strong: #5c4750; --tx-soft: #836c76; --tx-dim: #9c8590; --tx-faint: #b59eaa;
  --tx-mute: #ceb7c0; --amber-mute: #a3855f;
  --line-rgb: 231, 214, 220; --veil-rgb: 249, 240, 242;
  --bar-track: #f0dde3; --bar-tip: #dcc0c9; --apply-ink: #ffffff;
  --heat-1: #f2dde3; --heat-2: #e2b3c1; --heat-3: #d68da2; --heat-4: #bd6f88; --heat-5: #96506a;
}
/* peach 蜜桃乌龙 — warm peachy cream, cozy afternoon */
html[data-theme="peach"] {
  color-scheme: light;
  --page-bg: #faf1ea; --page-glow: rgba(217, 154, 118, .15);
  --acc-pink: #d99a76; --acc-pink-bright: #c98258; --acc-pink-soft: #e6b394;
  --acc-cyan: #97b3b7; --acc-cyan-bright: #85a3a8;
  --acc-violet: #b79eae; --acc-green: #a3ad85; --acc-amber: #d9b878;
  --panel-rgb: 255, 252, 248; --hero-rgb: 250, 242, 235; --ink-rgb: 243, 233, 224; --pop-rgb: 253, 249, 244;
  --pink-rgb: 217, 154, 118; --cyan-rgb: 151, 179, 183; --violet-rgb: 183, 158, 174;
  --green-rgb: 163, 173, 133; --amber-rgb: 217, 184, 120;
  --text-main: #443730; --surface-active: #ecd8c8;
  --tx-strong: #5e4c40; --tx-soft: #86715f; --tx-dim: #9f8a77; --tx-faint: #b9a592;
  --tx-mute: #d1bfae; --amber-mute: #9c8457;
  --line-rgb: 233, 219, 207; --veil-rgb: 250, 241, 234;
  --bar-track: #f0e2d4; --bar-tip: #dcc6b1; --apply-ink: #ffffff;
  --heat-1: #f4e0d0; --heat-2: #e6b998; --heat-3: #d99a76; --heat-4: #c07a4e; --heat-5: #96552f;
}
/* mint 薄荷奶昔 — fresh cool mint cream */
html[data-theme="mint"] {
  color-scheme: light;
  --page-bg: #ecf5f0; --page-glow: rgba(95, 184, 148, .14);
  --acc-pink: #5fb894; --acc-pink-bright: #4aa581; --acc-pink-soft: #86ccb0;
  --acc-cyan: #74b3c9; --acc-cyan-bright: #63a3ba;
  --acc-violet: #9ba8bd; --acc-green: #6db389; --acc-amber: #c9b078;
  --panel-rgb: 251, 254, 252; --hero-rgb: 238, 246, 242; --ink-rgb: 227, 238, 232; --pop-rgb: 247, 252, 249;
  --pink-rgb: 95, 184, 148; --cyan-rgb: 116, 179, 201; --violet-rgb: 155, 168, 189;
  --green-rgb: 109, 179, 137; --amber-rgb: 201, 176, 120;
  --text-main: #26382f; --surface-active: #c9e2d5;
  --tx-strong: #3b5044; --tx-soft: #5f7568; --tx-dim: #798d81; --tx-faint: #94a69b;
  --tx-mute: #adc0b5; --amber-mute: #8d7c52;
  --line-rgb: 205, 224, 213; --veil-rgb: 236, 245, 240;
  --bar-track: #dbeae1; --bar-tip: #bdd4c7; --apply-ink: #ffffff;
  --heat-1: #d3e8dc; --heat-2: #a4d2ba; --heat-3: #5fb894; --heat-4: #3f9a74; --heat-5: #2a7253;
}
"""

t = t.replace(anchor, themes + anchor)
p.write_text(t, encoding="utf-8")
print("4 gentle themes injected")
