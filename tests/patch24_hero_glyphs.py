# -*- coding: utf-8 -*-
"""patch24: hero heading text -> decorative glyph row.

User: drop "今天的输入节奏" heading words; show a small icon pattern instead.
The four glyphs echo the stat-card icons below (keys/mouse/hours/champion).
Also removes the now-unused rangeHeading computed (activeRangeLabel stays).
"""
import io
import sys

PATH = "src/App.vue"

REPLACEMENTS = [
    (
        '''      <div><h2>{{ rangeHeading }}的输入节奏</h2></div>
''',
        '''      <div class="hero-glyphs" aria-hidden="true"><i class="hg-k">✦</i><i class="hg-m">●</i><i class="hg-t">◷</i><i class="hg-c">♛</i></div>
''',
        1,
    ),
    (
        '''const activeRangeLabel = computed(() => activeRange.value === "自定义" ? `${customStart.value} → ${customEnd.value}` : activeRange.value);
const rangeHeading = computed(() => activeRange.value === "自定义" ? "选定范围" : activeRange.value);
''',
        '''const activeRangeLabel = computed(() => activeRange.value === "自定义" ? `${customStart.value} → ${customEnd.value}` : activeRange.value);
''',
        1,
    ),
]

CSS_TAIL = """
/* ---- hero glyph row (patch24): decorative icons replace heading text ---- */
.hero-glyphs { display: flex; align-items: center; gap: 10px; }
.hero-glyphs i { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px; font-style: normal; font-size: 15px; }
.hg-k { color: var(--acc-amber); background: rgba(var(--amber-rgb), .14); }
.hg-m { color: var(--acc-cyan); background: rgba(52, 217, 255, .13); }
.hg-t { color: var(--acc-violet); background: rgba(var(--violet-rgb), .14); }
.hg-c { color: var(--acc-pink-soft); background: rgba(var(--pink-rgb), .14); }
"""


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
        print("ok %d/%d" % (index, len(REPLACEMENTS)))
    marker = source.rfind("</style>")
    if marker < 0:
        print("ABORT: closing style tag not found")
        return 1
    source = source[:marker] + CSS_TAIL + "\n" + source[marker:]
    with io.open(PATH, "w", encoding="utf-8") as handle:
        handle.write(source)
    print("patched %s (%d bytes -> %d bytes)" % (PATH, len(original), len(source)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
