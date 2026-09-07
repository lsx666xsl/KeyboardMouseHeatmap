# -*- coding: utf-8 -*-
"""patch23: restore clear dashboard text; drop only decorative/marketing copy.

User feedback on patch22 (too bare): keep count text and clear card labels.
Restores card titles + range captions, keycap counts, panel headings,
legend, live footer, mouse labels, record/status pill text, footer actions.
Permanently removes only the "unsuitable" decorative pieces: English tagline
eyebrows (PERSONAL INPUT LAB / YOUR RHYTHM… / KEYBOARD MAP / MOUSE MAP /
TOP KEYS / ACTIVITY PULSE), the hero slogan line and hero copy paragraph,
and the confusing demo % / "已保存聚合" captions.
"""
import io
import sys

PATH = "src/App.vue"

REPLACEMENTS = [
    # 1. top status chip: readable label returns (live/warning/demo)
    (
        '''<div class="demo-chip" :class="{ warning: !demoMode && !inputAvailable, expanded: demoMode || !inputAvailable }" :title="demoMode ? '演示数据（浏览器预览）' : inputAvailable ? '本地实时数据' : '全局输入监听不可用'" aria-label="输入监听状态"><i></i><span v-if="demoMode || !inputAvailable">{{ demoMode ? "演示数据" : "监听不可用" }}</span></div>''',
        '''<div class="demo-chip" :class="{ warning: !demoMode && !inputAvailable }" :title="demoMode ? '演示数据（浏览器预览）' : inputAvailable ? '本地实时数据' : '全局输入监听不可用'"><i></i>{{ demoMode ? "演示数据" : inputAvailable ? "本地实时数据" : "监听不可用" }}</div>''',
        1,
    ),
    # 2. record pill: state text returns
    (
        '''<button class="record-button" :class="{ paused: !recording }" :disabled="!demoMode && !inputAvailable" :aria-label="recording ? '正在记录，点击暂停' : '已暂停，点击继续'" :title="!demoMode && !inputAvailable ? '全局输入监听不可用' : recording ? '正在记录 · 点击暂停' : '已暂停 · 点击继续'" @click="toggleRecording"><span class="record-dot"></span></button>''',
        '''<button class="record-button" :class="{ paused: !recording }" :disabled="!demoMode && !inputAvailable" :title="!demoMode && !inputAvailable ? '全局输入监听不可用' : ''" @click="toggleRecording"><span class="record-dot"></span>{{ recording ? "正在记录" : "已暂停" }}</button>''',
        1,
    ),
    # 3. hero: clear heading returns (slogan <em> + copy paragraph stay gone)
    (
        '''    <section class="hero-row">
      <div class="range-control">''',
        '''    <section class="hero-row">
      <div><h2>{{ rangeHeading }}的输入节奏</h2></div>
      <div class="range-control">''',
        1,
    ),
    # 4. stat cards: title + honest caption return (no fake demo %)
    (
        '''      <article class="stat-card stat-card-primary" :title="'总按键数 · ' + activeRangeLabel" aria-label="总按键数"><div class="card-icon icon-spark">✦</div><strong>{{ formatNumber(shownKeys) }}</strong></article>''',
        '''      <article class="stat-card stat-card-primary"><div class="card-icon icon-spark">✦</div><p>总按键数</p><strong>{{ formatNumber(shownKeys) }}</strong><span class="trend neutral">{{ activeRangeLabel }}</span></article>''',
        1,
    ),
    (
        '''      <article class="stat-card" :title="'鼠标操作 · ' + activeRangeLabel" aria-label="鼠标操作"><div class="card-icon icon-mouse">●</div><strong>{{ formatNumber(shownMouse) }}</strong></article>''',
        '''      <article class="stat-card"><div class="card-icon icon-mouse">●</div><p>鼠标操作</p><strong>{{ formatNumber(shownMouse) }}</strong><span class="trend neutral">{{ activeRangeLabel }}</span></article>''',
        1,
    ),
    (
        '''      <article class="stat-card" title="活跃小时数" aria-label="活跃小时数"><div class="card-icon icon-time">◷</div><strong>{{ activeHours }}<span class="unit">h</span></strong></article>''',
        '''      <article class="stat-card"><div class="card-icon icon-time">◷</div><p>活跃时段</p><strong>{{ activeHours }}<span class="unit">h</span></strong><span class="trend neutral">有输入的钟点数</span></article>''',
        1,
    ),
    (
        '''      <article class="stat-card highlight-card" title="当前范围冠军按键" aria-label="冠军按键"><div class="card-icon icon-top">♛</div><strong>{{ champion?.label ?? "—" }}</strong><span v-if="champion" class="champ-count">{{ formatNumber(champion.count) }}</span></article>''',
        '''      <article class="stat-card highlight-card"><div class="card-icon icon-top">♛</div><p>{{ activeRange === "今天" ? "今日冠军" : "范围冠军" }}</p><strong>{{ champion?.label ?? "暂无" }}</strong><span class="trend accent-text">{{ formatNumber(champion?.count ?? 0) }} 次按下</span></article>''',
        1,
    ),
    # 5. keyboard panel heading + legend (English eyebrow dropped)
    (
        '''      <article class="panel keyboard-panel">
        <div class="keyboard-wrap">''',
        '''      <article class="panel keyboard-panel">
        <div class="panel-heading"><h3>键盘热力图</h3><div class="legend"><span class="legend-gradient"></span><small>低</small><small>高</small></div></div>
        <div class="keyboard-wrap">''',
        1,
    ),
    # 6. keycaps: per-key count text returns (three distinct keycap templates)
    (
        '''<div v-for="key in row" :key="key.id" class="keycap" :class="[heatLevel(keyCount(key)), { muted: key.muted, blank: key.blank }]" :style="{ flex: `${key.width ?? 1} 1 0`, '--key-color': heatColor(keyCount(key)) }" :title="`${key.label}：${formatNumber(keyCount(key))} 次`"><span>{{ key.label }}</span></div>''',
        '''<div v-for="key in row" :key="key.id" class="keycap" :class="[heatLevel(keyCount(key)), { muted: key.muted, blank: key.blank }]" :style="{ flex: `${key.width ?? 1} 1 0`, '--key-color': heatColor(keyCount(key)) }" :title="`${key.label}：${formatNumber(keyCount(key))} 次`"><span>{{ key.label }}</span><b>{{ formatNumber(keyCount(key)) }}</b></div>''',
        1,
    ),
    (
        '''<div v-for="key in leftSideKeys" :key="key.id" class="keycap side" :style="{ gridArea: sideArea(key), '--key-color': heatColor(sideKeyCount(key)) }" :title="`${key.label}：${formatNumber(sideKeyCount(key))} 次`"><span>{{ key.label }}</span></div>''',
        '''<div v-for="key in leftSideKeys" :key="key.id" class="keycap side" :style="{ gridArea: sideArea(key), '--key-color': heatColor(sideKeyCount(key)) }" :title="`${key.label}：${formatNumber(sideKeyCount(key))} 次`"><span>{{ key.label }}</span><b>{{ formatNumber(sideKeyCount(key)) }}</b></div>''',
        1,
    ),
    (
        '''<div v-for="key in numSideKeys" :key="key.id" class="keycap side" :style="{ gridArea: sideArea(key), '--key-color': heatColor(sideKeyCount(key)) }" :title="`${key.label}：${formatNumber(sideKeyCount(key))} 次`"><span>{{ key.label }}</span></div>''',
        '''<div v-for="key in numSideKeys" :key="key.id" class="keycap side" :style="{ gridArea: sideArea(key), '--key-color': heatColor(sideKeyCount(key)) }" :title="`${key.label}：${formatNumber(sideKeyCount(key))} 次`"><span>{{ key.label }}</span><b>{{ formatNumber(sideKeyCount(key)) }}</b></div>''',
        1,
    ),
    # 7. keyboard footer status line returns (placed back after the keyboard wrap)
    (
        '''        </div>
      </article>

      <div class="side-column">''',
        '''        </div>
        <div class="keyboard-footer"><span><i class="live-indicator"></i>{{ demoMode ? "界面预览数据" : "数据实时更新中" }}</span><span>按键总量 · {{ formatNumber(totalKeyPresses) }}</span></div>
      </article>

      <div class="side-column">''',
        1,
    ),
    # 8. mouse panel: heading, in-shape counts and action names return
    (
        '''        <article class="panel mouse-panel">
          <div class="mouse-content"><div class="mouse-shape" aria-label="鼠标模板"><div class="mouse-top"><div class="mouse-button mouse-left"></div><div class="mouse-button mouse-right"></div><div class="mouse-wheel"><i></i></div></div><div class="mouse-side-buttons"><i></i><i></i></div></div><div class="mouse-stats"><div v-for="item in mouseStats" :key="item.label" class="mouse-stat" :title="item.label"><i :style="{ background: item.color }"></i><b>{{ formatNumber(item.value) }}</b></div></div></div>''',
        '''        <article class="panel mouse-panel">
          <div class="panel-heading compact"><h3>鼠标热力图</h3><span class="panel-kicker">{{ formatNumber(totalMouseActions) }} 次</span></div>
          <div class="mouse-content"><div class="mouse-shape" aria-label="鼠标模板"><div class="mouse-top"><div class="mouse-button mouse-left"><span>{{ formatNumber(mouseStats[0].value) }}</span></div><div class="mouse-button mouse-right"><span>{{ formatNumber(mouseStats[1].value) }}</span></div><div class="mouse-wheel"><i></i></div></div><div class="mouse-side-buttons"><i></i><i></i></div></div><div class="mouse-stats"><div v-for="item in mouseStats" :key="item.label" class="mouse-stat"><i :style="{ background: item.color }"></i><span>{{ item.label }}</span><b>{{ formatNumber(item.value) }}</b></div></div></div>''',
        1,
    ),
    # 9. top-keys panel heading returns
    (
        '''        <article class="panel top-keys-panel">
          <div class="top-key-list">''',
        '''        <article class="panel top-keys-panel">
          <div class="panel-heading compact"><h3>高频按键</h3><span class="sparkline">╱╲╱╲╱╱╲</span></div>
          <div class="top-key-list">''',
        1,
    ),
    # 10. timeline panel heading returns (English eyebrow dropped)
    (
        '''    <section class="panel timeline-panel" :title="rangeHeading + ' · 峰值 ' + String(peakHour).padStart(2, '0') + ':00'" aria-label="活跃节奏时间轴">''',
        '''    <section class="panel timeline-panel"><div class="panel-heading compact"><h3>一天中的活跃节奏</h3><span class="timeline-note">峰值时段 <b>{{ String(peakHour).padStart(2, "0") }}:00</b></span></div>''',
        1,
    ),
    # 11. footer: text actions + privacy note return (English brand line dropped)
    (
        '''    <footer class="footer-note"><button class="footer-action" aria-label="清空本地统计数据" title="清空本地统计数据" :disabled="demoMode" @click="clearStats">🗑</button><button class="footer-action" aria-label="每日足迹卡" title="每日足迹卡" @click="openFootprintCard">✦</button><button class="footer-action pk" aria-label="PK 对战" title="PK 对战" @click="showPkDuel = true">⚔</button></footer>''',
        '''    <footer class="footer-note"><span>隐私优先 · 只保存聚合统计，不保存输入文本</span><button class="clear-button" :disabled="demoMode" @click="clearStats">清空本地数据</button><button class="footprint-button" @click="openFootprintCard">✦ 足迹卡</button><button class="footprint-button pk-launch" @click="showPkDuel = true">⚔ PK 对战</button></footer>''',
        1,
    ),
]

CSS_REMOVE_START = "/* ---- minimal dashboard (patch22): text-free resting view ----"


def main() -> int:
    with io.open(PATH, "r", encoding="utf-8") as handle:
        source = handle.read()

    original = source
    for index, (old, new, expected) in enumerate(REPLACEMENTS, start=1):
        occurrences = source.count(old)
        if occurrences != expected:
            print("ABORT at replacement %d: expected %d occurrence(s), found %d" % (index, expected, occurrences))
            print("anchor head: %r" % old[:110])
            return 1
        source = source.replace(old, new)
        print("ok %2d/%-2d (%d hit%s)" % (index, len(REPLACEMENTS), expected, "" if expected == 1 else "s"))

    start_marker = source.find(CSS_REMOVE_START)
    if start_marker < 0:
        print("ABORT: patch22 CSS block not found")
        return 1
    close_marker = source.find("</style>", start_marker)
    if close_marker < 0:
        print("ABORT: closing style tag not found")
        return 1
    source = source[:start_marker] + source[close_marker:]
    print("ok     patch22 CSS overrides removed")

    with io.open(PATH, "w", encoding="utf-8") as handle:
        handle.write(source)
    print("patched %s (%d bytes -> %d bytes)" % (PATH, len(original), len(source)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
