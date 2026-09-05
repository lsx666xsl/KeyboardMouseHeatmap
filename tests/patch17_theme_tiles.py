"""Theme picker: grouped compact tiles + 4 new gentle themes + portal to in-page host."""
import re
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# ---- 1) inject 4 gentle theme CSS blocks ----
anchor = "/* latte 拿铁暖白 — warm paper-light, caramel & cream (calm, low glare) */"
assert anchor in t
extra_themes = """
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
  --acc-cyan: #96aec0; --acc-cyan-bright: #849eb2;
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
t = t.replace(anchor, extra_themes + anchor)

# ---- 2) replace themeOptions data with grouped entries ----
arr_start = t.find("const themeOptions: ThemeOption[] = [")
arr_end = t.find("];", arr_start) + 2
assert arr_start != -1
new_arr = """const themeOptions: ThemeOption[] = [
  { id: "latte", name: "拿铁暖白", group: "温和纸感", dots: ["#b98a5e", "#7f97a5", "#a590a8"] },
  { id: "sage", name: "鼠尾草绿", group: "温和纸感", dots: ["#7ba889", "#7ea3b0", "#c7a25f"] },
  { id: "matcha", name: "抹茶和纸", group: "温和纸感", dots: ["#8a9a5b", "#7e9a8b", "#d0a259"] },
  { id: "dusk", name: "暮云蓝", group: "温和纸感", dots: ["#8fa8c9", "#7fb2c4", "#a191c4"] },
  { id: "cocoa", name: "可可陶土", group: "温和纸感", dots: ["#c98d6d", "#a89a86", "#d9b37a"] },
  { id: "mist-blue", name: "雾蓝清晨", group: "温和纸感", dots: ["#6d9bc3", "#6fa3b8", "#c2a878"] },
  { id: "indigo-night", name: "靛夜静谧", group: "温和纸感", dots: ["#7d9ecb", "#79a8c0", "#9a94c9"] },
  { id: "lavender", name: "薰衣草", group: "温和纸感", dots: ["#9b8cc4", "#8ba3bd", "#c7ab7e"] },
  { id: "sakura", name: "樱花三月", group: "温和纸感", dots: ["#d68da2", "#96aec0", "#d3b183"] },
  { id: "peach", name: "蜜桃乌龙", group: "温和纸感", dots: ["#d99a76", "#97b3b7", "#d9b878"] },
  { id: "mint", name: "薄荷奶昔", group: "温和纸感", dots: ["#5fb894", "#74b3c9", "#c9b078"] },
  { id: "graphite", name: "苹果石墨", group: "苹果质感", dots: ["#0a84ff", "#ff375f", "#30d158"] },
  { id: "starlight", name: "星光浅色", group: "苹果质感", dots: ["#007aff", "#ff9f0a", "#34c759"] },
  { id: "neon", name: "霓虹之夜", group: "高饱和霓虹", dots: ["#ff5c7a", "#34d9ff", "#a78bfa"] },
  { id: "ocean", name: "深海回声", group: "高饱和霓虹", dots: ["#2dd4bf", "#38bdf8", "#818cf8"] },
  { id: "sunset", name: "落日熔金", group: "高饱和霓虹", dots: ["#fb923c", "#f472b6", "#fbbf24"] },
  { id: "aurora", name: "极光森林", group: "高饱和霓虹", dots: ["#34d399", "#22d3ee", "#a3e635"] },
  { id: "neon-drive", name: "霓虹夜驰", group: "高饱和霓虹", dots: ["#ff2fd4", "#05f4ff", "#7b2cff"] },
  { id: "miami", name: "迈阿密海岸", group: "高饱和霓虹", dots: ["#ff5e9f", "#3ae7ff", "#09fbd3"] },
  { id: "sunset-horizon", name: "落日地平线", group: "高饱和霓虹", dots: ["#ff006e", "#9d4edd", "#ffd670"] },
  { id: "laser-horizon", name: "镭射地平线", group: "高饱和霓虹", dots: ["#ff3f8e", "#ff8a3d", "#7b2cff"] },
  { id: "cyber-alley", name: "赛博雨巷", group: "高饱和霓虹", dots: ["#fe53bb", "#08f7fe", "#f5d300"] },
  { id: "volt", name: "荧光青柠", group: "高饱和霓虹", dots: ["#ccff00", "#00ff9d", "#00e5ff"] },
];
const themeGroupOrder = ["温和纸感", "苹果质感", "高饱和霓虹"];
const themeGroups = themeGroupOrder.map((name) => ({
  name,
  items: themeOptions.filter((option) => option.group === name),
}));"""
t = t[:arr_start] + new_arr + t[arr_end:]

# type gains group
t = t.replace("type ThemeOption = { id: string; name: string; dots: string[] };",
              "type ThemeOption = { id: string; name: string; group: string; dots: string[] };")

# ---- 3) settings theme pane: grouped compact tiles ----
old_pane_start = t.find('<div class="settings-themes" role="radiogroup" aria-label="主题配色">')
pane_end = t.find("</div>", old_pane_start)
old_block = t[old_pane_start:t.find("</div>", t.find("</div>", old_pane_start)) + 6]
new_block = """<div class="theme-groups">
                <div v-for="group in themeGroups" :key="group.name" class="theme-group">
                  <small>{{ group.name }} · {{ group.items.length }}</small>
                  <div class="theme-tiles" role="radiogroup" :aria-label="group.name">
                    <button v-for="option in group.items" :key="option.id" role="radio" :aria-checked="themeId === option.id" :class="{ active: themeId === option.id }" class="theme-tile" @click="applyTheme(option.id)"><span class="tile-dots"><i v-for="(dot, dotIndex) in option.dots" :key="dotIndex" :style="{ background: dot }"></i></span><span class="tile-name">{{ option.name }}</span></button>
                  </div>
                </div>
              </div>"""
t = t.replace(old_block, new_block)

# ---- 4) CSS: replace settings-themes styles with tiles ----
css_start = t.find(".settings-themes { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; }")
css_end = t.find(".setting-theme.active {", css_start)
assert css_start != -1 and css_end != -1
# find end of .setting-theme.active rule
css_end = t.find("}", css_end) + 1
new_css = """.theme-groups { display: grid; gap: 10px; max-height: 380px; overflow: auto; padding-right: 4px; }
.theme-group small { display: block; margin-bottom: 5px; color: var(--tx-faint); font-size: 8px; font-weight: 800; letter-spacing: .12em; }
.theme-tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }
.theme-tile { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 7px 3px 6px; border: 1px solid rgba(var(--line-rgb), .14); border-radius: 10px; background: rgba(var(--ink-rgb), .25); cursor: pointer; transition: all .14s ease; }
.theme-tile:hover { border-color: rgba(var(--cyan-rgb), .5); }
.theme-tile.active { border-color: rgba(var(--cyan-rgb), .7); background: rgba(var(--cyan-rgb), .1); box-shadow: 0 0 10px rgba(var(--cyan-rgb), .12); }
.tile-dots { display: flex; gap: 2px; }
.tile-dots i { width: 7px; height: 7px; border-radius: 50%; display: block; box-shadow: inset 0 0 0 1px rgba(255,255,255,.25); }
.tile-name { color: var(--tx-soft); font-size: 8.5px; font-weight: 700; white-space: nowrap; }
.theme-tile.active .tile-name { color: var(--text-main); }"""
t = t[:css_start] + new_css + t[css_end:]

p.write_text(t, encoding="utf-8")
print("themes grouped + 4 added + tiles compact")
