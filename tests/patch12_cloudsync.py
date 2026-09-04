"""Replay App.vue cloud-sync additions carefully on top of clean HEAD."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# 1) add cloud sync section right BEFORE the wireSoundFx definition (outside any fn)
anchor = "let stopKeySoundListener: UnlistenFn | undefined;\nasync function wireSoundFx() {"
assert anchor in t, "anchor missing"
addition = """// ---------- cloud daily stats sync (leaderboard data) ----------
let cloudSyncTimer: ReturnType<typeof setInterval> | undefined;

async function cloudSyncToday() {
  const server = localStorage.getItem("kp-cloud-server");
  const token = localStorage.getItem("kp-cloud-token");
  if (!server || !token || demoMode.value) return;
  const today = new Date().toISOString().slice(0, 10);
  try {
    const dashboard = await fetchActiveDashboard();
    await fetch(server + "/api/stats", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        token,
        date: today,
        keys: dashboard.totalKeyPresses,
        mouse: dashboard.totalMouseActions,
      }),
    });
  } catch {
    // offline or server down; try again next tick
  }
}

""" + anchor
t = t.replace(anchor, addition)

# 2) hook into main-window mount/unmount
old_mount = """    connectToRuntime();
    wireSoundFx();"""
assert old_mount in t
t = t.replace(old_mount, """    connectToRuntime();
    wireSoundFx();
    cloudSyncToday();
    cloudSyncTimer = setInterval(cloudSyncToday, 60_000);""")

old_un = """  stopKeySoundListener?.();
  stopMetronome();"""
assert old_un in t
t = t.replace(old_un, """  stopKeySoundListener?.();
  stopMetronome();
  if (cloudSyncTimer) clearInterval(cloudSyncTimer);""")

p.write_text(t, encoding="utf-8")
print("cloud sync replayed")
