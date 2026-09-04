"""Replay patch 5: PK duel integration (footer button + host)."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

anchor = 'import DailyCard from "./DailyCard.vue";'
assert anchor in t
t = t.replace(anchor, anchor + '\nimport PkDuel from "./PkDuel.vue";')

anchor2 = 'const showFootprintCard = ref(false);'
assert anchor2 in t
t = t.replace(anchor2, anchor2 + '\nconst showPkDuel = ref(false);')

# footer duel button next to footprint
old_footer = '<button class="clear-button" :disabled="demoMode" @click="clearStats">清空本地数据</button><button class="footprint-button" @click="openFootprintCard">✦ 足迹卡</button>'
assert old_footer in t
t = t.replace(old_footer, '<button class="clear-button" :disabled="demoMode" @click="clearStats">清空本地数据</button><button class="footprint-button" @click="openFootprintCard">✦ 足迹卡</button><button class="footprint-button pk-launch" @click="showPkDuel = true">⚔ PK 对战</button>')

# modal host near DailyCard host
old_host = '<DailyCard v-if="showFootprintCard && footprintSnapshot"'
assert old_host in t
t = t.replace(old_host, '<PkDuel v-if="showPkDuel" @close="showPkDuel = false" />\n    <DailyCard v-if="showFootprintCard && footprintSnapshot"')

# pk launch accent
anchor_css = ".footprint-button:hover { color: var(--acc-pink-soft); }"
assert anchor_css in t
t = t.replace(anchor_css, anchor_css + "\n.pk-launch:hover { color: var(--acc-cyan-bright); }")

p.write_text(t, encoding="utf-8")
print("patch5 applied")
