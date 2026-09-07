# -*- coding: utf-8 -*-
"""patch22: strip decorative text from the KeyPulse main dashboard.

Resting view keeps only icons/glyphs and data numbers; every removed
label survives as a hover :title / aria-label tooltip. Scope is the main
dashboard only - settings / account / theme pages keep their text.
Apply atomically: every anchor must match exactly once (or the stated
count), otherwise the file is left untouched and the patch exits 1.
"""
import io
import sys

PATH = "src/App.vue"

# (old, new, expected occurrences) - applied in order.
REPLACEMENTS = [
    # 1. brand eyebrow (decorative English caption) removed
    (
        "<div><p class=\"eyebrow\">PERSONAL INPUT LAB</p><h1>Key<span>Pulse</span></h1></div>",
        "<div><h1>Key<span>Pulse</span></h1></div>",
        1,
    ),
    # 2. top status chip -> silent dot when live; label only for demo/warning states
    (
        '<div class="demo-chip" :class="{ warning: !demoMode && !inputAvailable }"><i></i> {{ demoMode ? "演示数据" : inputAvailable ? "本地实时数据" : "监听不可用" }}</div>',
        '<div class="demo-chip" :class="{ warning: !demoMode && !inputAvailable, expanded: demoMode || !inputAvailable }" :title="demoMode ? \'演示数据（浏览器预览）\' : inputAvailable ? \'本地实时数据\' : \'全局输入监听不可用\'" aria-label="输入监听状态"><i></i><span v-if="demoMode || !inputAvailable">{{ demoMode ? "演示数据" : "监听不可用" }}</span></div>',
        1,
    ),
    # 3. record pill -> round indicator dot with hover/aria state text
    (
        '<button class="record-button" :class="{ paused: !recording }" :disabled="!demoMode && !inputAvailable" :title="!demoMode && !inputAvailable ? \'全局输入监听不可用\' : \'\'" @click="toggleRecording"><span class="record-dot"></span>{{ recording ? "正在记录" : "已暂停" }}</button>',
        '<button class="record-button" :class="{ paused: !recording }" :disabled="!demoMode && !inputAvailable" :aria-label="recording ? \'正在记录，点击暂停\' : \'已暂停，点击继续\'" :title="!demoMode && !inputAvailable ? \'全局输入监听不可用\' : recording ? \'正在记录 · 点击暂停\' : \'已暂停 · 点击继续\'" @click="toggleRecording"><span class="record-dot"></span></button>',
        1,
    ),
    # 4. hero headline block removed (range control keeps the row)
    (
        "      <div><p class=\"eyebrow accent\">YOUR RHYTHM, VISUALIZED</p><h2>{{ rangeHeading }}的输入节奏<br /><em>每一次动作都算数。</em></h2><p class=\"hero-copy\">看见每一次敲击、点击和滚动，找到属于你的数字节奏。</p></div>\n",
        "",
        1,
    ),
    # 5. stat cards: icon + number only; labels become hover/aria text
    (
        '<article class="stat-card stat-card-primary"><div class="card-icon icon-spark">✦</div><p>总按键数</p><strong>{{ formatNumber(shownKeys) }}</strong><span class="trend" :class="demoMode ? \'up\' : \'neutral\'">{{ demoMode ? "↗ 12.8%" : "⌁ 已保存聚合" }} <small>{{ demoMode ? "对比昨日" : activeRangeLabel }}</small></span></article>',
        '<article class="stat-card stat-card-primary" :title="\'总按键数 · \' + activeRangeLabel" aria-label="总按键数"><div class="card-icon icon-spark">✦</div><strong>{{ formatNumber(shownKeys) }}</strong></article>',
        1,
    ),
    (
        '<article class="stat-card"><div class="card-icon icon-mouse">●</div><p>鼠标操作</p><strong>{{ formatNumber(shownMouse) }}</strong><span class="trend" :class="demoMode ? \'up\' : \'neutral\'">{{ demoMode ? "↗ 8.4%" : "⌁ 已保存聚合" }} <small>{{ demoMode ? "对比昨日" : activeRangeLabel }}</small></span></article>',
        '<article class="stat-card" :title="\'鼠标操作 · \' + activeRangeLabel" aria-label="鼠标操作"><div class="card-icon icon-mouse">●</div><strong>{{ formatNumber(shownMouse) }}</strong></article>',
        1,
    ),
    (
        '<article class="stat-card"><div class="card-icon icon-time">◷</div><p>活跃时段</p><strong>{{ activeHours }}<span class="unit">h</span></strong><span class="trend neutral">⌁ 按小时聚合统计</span></article>',
        '<article class="stat-card" title="活跃小时数" aria-label="活跃小时数"><div class="card-icon icon-time">◷</div><strong>{{ activeHours }}<span class="unit">h</span></strong></article>',
        1,
    ),
    (
        '<article class="stat-card highlight-card"><div class="card-icon icon-top">♛</div><p>{{ activeRange === "今天" ? "今日冠军" : "范围冠军" }}</p><strong>{{ champion?.label ?? "暂无" }}</strong><span class="trend accent-text">{{ formatNumber(champion?.count ?? 0) }} 次按下</span></article>',
        '<article class="stat-card highlight-card" title="当前范围冠军按键" aria-label="冠军按键"><div class="card-icon icon-top">♛</div><strong>{{ champion?.label ?? "—" }}</strong><span v-if="champion" class="champ-count">{{ formatNumber(champion.count) }}</span></article>',
        1,
    ),
    # 6. keyboard / mouse / top-keys panel titles + legend removed
    (
        '        <div class="panel-heading"><div><p class="eyebrow">KEYBOARD MAP</p><h3>键盘热力图</h3></div><div class="legend"><span class="legend-gradient"></span><small>低</small><small>高</small></div></div>\n',
        "",
        1,
    ),
    (
        '          <div class="panel-heading compact"><div><p class="eyebrow">MOUSE MAP</p><h3>鼠标热力图</h3></div><span class="panel-kicker">{{ formatNumber(totalMouseActions) }} actions</span></div>\n',
        "",
        1,
    ),
    (
        '          <div class="panel-heading compact"><div><p class="eyebrow">TOP KEYS</p><h3>高频按键</h3></div><span class="sparkline">╱╲╱╲╱╱╲</span></div>\n',
        "",
        1,
    ),
    # 7. keyboard footer status line removed (topbar chip covers live status)
    (
        '        <div class="keyboard-footer"><span><i class="live-indicator"></i>{{ demoMode ? "界面预览数据" : "数据实时更新中" }}</span><span>按键总量 · {{ formatNumber(totalKeyPresses) }}</span></div>\n',
        "",
        1,
    ),
    # 8. keycaps: keep the letter, drop the per-key count (hover still shows it)
    (
        '<span>{{ key.label }}</span><b>{{ formatNumber(keyCount(key)) }}</b>',
        "<span>{{ key.label }}</span>",
        1,
    ),
    (
        '<span>{{ key.label }}</span><b>{{ formatNumber(sideKeyCount(key)) }}</b>',
        "<span>{{ key.label }}</span>",
        2,
    ),
    # 9. mouse shape: plain coloured halves without the duplicated numbers
    (
        '<div class="mouse-button mouse-left"><span>{{ formatNumber(mouseStats[0].value) }}</span></div><div class="mouse-button mouse-right"><span>{{ formatNumber(mouseStats[1].value) }}</span></div>',
        '<div class="mouse-button mouse-left"></div><div class="mouse-button mouse-right"></div>',
        1,
    ),
    # 10. mouse action rows: dot + value; action name on hover
    (
        '<div v-for="item in mouseStats" :key="item.label" class="mouse-stat"><i :style="{ background: item.color }"></i><span>{{ item.label }}</span><b>{{ formatNumber(item.value) }}</b></div>',
        '<div v-for="item in mouseStats" :key="item.label" class="mouse-stat" :title="item.label"><i :style="{ background: item.color }"></i><b>{{ formatNumber(item.value) }}</b></div>',
        1,
    ),
    # 11. timeline panel: title/peak note folded into hover text
    (
        '    <section class="panel timeline-panel"><div class="panel-heading compact"><div><p class="eyebrow">ACTIVITY PULSE · {{ activeRangeLabel }}</p><h3>一天中的活跃节奏</h3></div><span class="timeline-note">峰值时段 <b>{{ String(peakHour).padStart(2, "0") }}:00</b></span></div>',
        '    <section class="panel timeline-panel" :title="rangeHeading + \' · 峰值 \' + String(peakHour).padStart(2, \'0\') + \':00\'" aria-label="活跃节奏时间轴">',
        1,
    ),
    # 12. footer: icon-only actions; brand/privacy lines removed
    (
        '<footer class="footer-note"><span>KeyPulse · offline by design</span><span>隐私优先 · 只保存聚合统计，不保存输入文本</span><button class="clear-button" :disabled="demoMode" @click="clearStats">清空本地数据</button><button class="footprint-button" @click="openFootprintCard">✦ 足迹卡</button><button class="footprint-button pk-launch" @click="showPkDuel = true">⚔ PK 对战</button></footer>',
        '<footer class="footer-note"><button class="footer-action" aria-label="清空本地统计数据" title="清空本地统计数据" :disabled="demoMode" @click="clearStats">🗑</button><button class="footer-action" aria-label="每日足迹卡" title="每日足迹卡" @click="openFootprintCard">✦</button><button class="footer-action pk" aria-label="PK 对战" title="PK 对战" @click="showPkDuel = true">⚔</button></footer>',
        1,
    ),
]

CSS_TAIL = """
/* ---- minimal dashboard (patch22): text-free resting view ----
   Everything removed above is still reachable via hover :title. */
.hero-row { justify-content: flex-end; margin-bottom: 24px; }
.stat-card { display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
.champ-count { margin-top: -6px; color: var(--acc-pink-soft); font-size: 14px; font-weight: 700; }
.keycap { justify-content: center; }
.demo-chip { width: 34px; height: 34px; padding: 0; justify-content: center; border-radius: 50%; flex: 0 0 auto; }
.demo-chip.expanded { width: auto; height: auto; padding: 9px 13px; border-radius: 999px; }
.record-button { width: 34px; height: 34px; padding: 0; justify-content: center; border-radius: 50%; flex: 0 0 auto; }
.footer-note { justify-content: flex-end; }
.footer-action { display: grid; place-items: center; width: 32px; height: 32px; border: 1px solid rgba(var(--line-rgb),.15); border-radius: 50%; background: rgba(var(--panel-rgb),.55); color: var(--tx-soft); cursor: pointer; font-size: 13px; transition: border-color .2s ease, color .2s ease, transform .2s ease; }
.footer-action:hover:not(:disabled) { border-color: rgba(var(--cyan-rgb),.6); color: #fff; transform: translateY(-1px); }
.footer-action:disabled { cursor: not-allowed; opacity: .35; }
.footer-action.pk { color: var(--acc-pink-bright); }
.mouse-stat b { font-variant-numeric: tabular-nums; }
"""


def main() -> int:
    with io.open(PATH, "r", encoding="utf-8") as handle:
        source = handle.read()

    original = source
    for index, (old, new, expected) in enumerate(REPLACEMENTS, start=1):
        occurrences = source.count(old)
        if occurrences != expected:
            print("ABORT at replacement %d: expected %d occurrence(s), found %d" % (index, expected, occurrences))
            print("anchor head: %r" % old[:90])
            return 1
        source = source.replace(old, new)
        print("ok %2d/%-2d (%d hit%s)" % (index, len(REPLACEMENTS), expected, "" if expected == 1 else "s"))

    close_marker = "</style>"
    marker_index = source.rfind(close_marker)
    if marker_index < 0:
        print("ABORT: could not locate closing </style> tag")
        return 1
    source = source[:marker_index] + CSS_TAIL + "\n" + source[marker_index:]

    with io.open(PATH, "w", encoding="utf-8") as handle:
        handle.write(source)
    print("patched %s (%d bytes -> %d bytes)" % (PATH, len(original), len(source)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
