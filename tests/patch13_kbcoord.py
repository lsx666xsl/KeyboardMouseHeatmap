"""Replace side-keyboard model with explicit coordinate layout and fix template/css."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# ---- A) replace data region (sideBlocks/sideColumns/sideItems/sideGridRow) with coordinate model ----
start = t.find("// Full-104 side zones")
end = t.find("const sideKeyColumnCounts")
assert start != -1 and end != -1 and start < end
new_model = """// Right side of the real 104 layout as coordinate grids over 6 rows that
// mirror the main keyboard rows: edit keys on rows 2-3 with the direction pad
// right beneath them (rows 4-5, under the PrtSc column), and the numeric
// keypad on rows 2-6 with true key spans (+/Enter double-height, 0 wide).
type SideKeySpec = { id: string; label: string; row: number; col: number; rowspan?: number; colspan?: number };
const leftSideKeys: SideKeySpec[] = [
  { id: "insert", label: "Ins", row: 2, col: 1 },
  { id: "home", label: "Home", row: 2, col: 2 },
  { id: "page-up", label: "PgUp", row: 2, col: 3 },
  { id: "delete", label: "Del", row: 3, col: 1 },
  { id: "end", label: "End", row: 3, col: 2 },
  { id: "page-down", label: "PgDn", row: 3, col: 3 },
  { id: "arrow-up", label: "↑", row: 4, col: 2, rowspan: 2 },
  { id: "arrow-left", label: "←", row: 5, col: 1 },
  { id: "arrow-down", label: "↓", row: 5, col: 2 },
  { id: "arrow-right", label: "→", row: 5, col: 3 },
];
const numSideKeys: SideKeySpec[] = [
  { id: "num-lock", label: "Num", row: 2, col: 1 },
  { id: "numpad-divide", label: "/", row: 2, col: 2 },
  { id: "numpad-multiply", label: "*", row: 2, col: 3 },
  { id: "numpad-subtract", label: "-", row: 2, col: 4 },
  { id: "numpad-7", label: "7", row: 3, col: 1 },
  { id: "numpad-8", label: "8", row: 3, col: 2 },
  { id: "numpad-9", label: "9", row: 3, col: 3 },
  { id: "numpad-add", label: "+", row: 3, col: 4, rowspan: 2 },
  { id: "numpad-4", label: "4", row: 4, col: 1 },
  { id: "numpad-5", label: "5", row: 4, col: 2 },
  { id: "numpad-6", label: "6", row: 4, col: 3 },
  { id: "numpad-1", label: "1", row: 5, col: 1 },
  { id: "numpad-2", label: "2", row: 5, col: 2 },
  { id: "numpad-3", label: "3", row: 5, col: 3 },
  { id: "numpad-enter", label: "↵", row: 5, col: 4, rowspan: 2 },
  { id: "numpad-0", label: "0", row: 6, col: 1, colspan: 2 },
  { id: "numpad-decimal", label: ".", row: 6, col: 3 },
];
function sideArea(spec: SideKeySpec) {
  return spec.row + " / " + spec.col + " / span " + (spec.rowspan || 1) + " / span " + (spec.colspan || 1);
}
"""
t = t[:start] + new_model + t[end:]

# ---- B) template: replace kb-side block ----
tmpl_start = t.find('          <div class="kb-side">')
tmpl_end_marker = '        </div>\n        <div class="keyboard-footer">'
tmpl_end = t.find(tmpl_end_marker, tmpl_start)
assert tmpl_start != -1 and tmpl_end != -1
new_tmpl = """          <div class="kb-side">
            <div class="kb-right-block">
              <div v-for="key in leftSideKeys" :key="key.id" class="keycap side" :style="{ gridArea: sideArea(key), '--key-color': heatColor(sideKeyCount(key)) }" :title="`${key.label}：${formatNumber(sideKeyCount(key))} 次`"><span>{{ key.label }}</span><b>{{ formatNumber(sideKeyCount(key)) }}</b></div>
            </div>
            <div class="kb-right-block num">
              <div v-for="key in numSideKeys" :key="key.id" class="keycap side" :style="{ gridArea: sideArea(key), '--key-color': heatColor(sideKeyCount(key)) }" :title="`${key.label}：${formatNumber(sideKeyCount(key))} 次`"><span>{{ key.label }}</span><b>{{ formatNumber(sideKeyCount(key)) }}</b></div>
            </div>
          </div>
"""
t = t[:tmpl_start] + new_tmpl + t[tmpl_end:]

# ---- C) CSS: replace old right columns rules with block grids ----
old_css_start = t.find(".kb-side { display: flex; gap: .9cqw;")
old_css_end = t.find(".keycap.warm {")
assert old_css_start != -1 and old_css_end != -1 and old_css_start < old_css_end
new_css = """.kb-side { display: flex; gap: 1cqw; flex: 0 0 auto; align-items: start; }
.kb-right-block { display: grid; grid-template-rows: repeat(6, 5.1cqw); gap: .5cqw; }
.kb-right-block { grid-template-columns: repeat(3, minmax(3.2cqw, auto)); }
.kb-right-block.num { grid-template-columns: repeat(4, minmax(3.4cqw, auto)); }
"""
t = t[:old_css_start] + new_css + t[old_css_end:]

p.write_text(t, encoding="utf-8")
print("coordinate keyboard model applied")
