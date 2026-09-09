// ============================================================
// Auto-updater (main window, production builds only).
//
// Checks the GitHub Releases `latest.json` endpoint on startup
// and every 6 hours while the app is running, downloads the new
// installer in the background and offers a one-click install.
// On Windows `downloadAndInstall` exits the app after launching
// the installer, which relaunches it — no manual restart needed.
//
// The tray menu item "检查更新" re-triggers a check via the
// `check-update` event (manual checks ignore "dismissed" state).
// ============================================================
import { check, type Update, type DownloadEvent } from "@tauri-apps/plugin-updater";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { listen } from "@tauri-apps/api/event";

let started = false;
let busy = false; // a download/install is already in flight
let current: Update | null = null;

const AUTO_CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000;
const DISMISSED_KEY = "keypulse-updater-dismissed";

export async function initUpdater(): Promise<void> {
  if (started || import.meta.env.DEV) return;
  try {
    if (getCurrentWindow().label !== "main") return;
  } catch {
    return; // plain-browser preview without a Tauri window
  }
  started = true;
  listen("check-update", () => void checkForUpdate(true)).catch(() => undefined);
  window.setTimeout(() => void checkForUpdate(false), 2500);
  window.setInterval(() => void checkForUpdate(false), AUTO_CHECK_INTERVAL_MS);
}

async function checkForUpdate(manual: boolean): Promise<void> {
  if (busy || !currentIsHidden()) return;
  try {
    const update = await check();
    if (!update) return;
    current = update;
    if (!manual && localStorage.getItem(DISMISSED_KEY) === update.version) return;
    showCard({ kind: "found", version: update.version });
  } catch (error) {
    if (manual) {
      showCard({ kind: "error", message: errorMessage(error) });
    }
    console.info("KeyPulse update check failed:", error);
  }
}

// ============================= card UI =============================

type View =
  | { kind: "hidden" }
  | { kind: "found"; version: string }
  | { kind: "downloading"; percent: number | null }
  | { kind: "installing" }
  | { kind: "error"; message: string };

let view: View = { kind: "hidden" };
let card: HTMLDivElement | null = null;

function ensureCard(): HTMLDivElement {
  if (card) return card;
  card = document.createElement("div");
  card.className = "kp-updater";
  card.addEventListener("click", (event) => {
    const button = (event.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!button) return;
    void handleAction(button.dataset.action);
  });
  document.body.appendChild(card);
  return card;
}

async function handleAction(action?: string): Promise<void> {
  if (!current) return;
  if (action === "install") {
    busy = true;
    showCard({ kind: "downloading", percent: null });
    try {
      await current.downloadAndInstall((event: DownloadEvent) => {
        switch (event.event) {
          case "Started":
            showCard({ kind: "downloading", percent: null });
            break;
          case "Progress": {
            const data = event.data as { downloaded?: number; contentLength?: number };
            const percent =
              data.contentLength && data.contentLength > 0
                ? Math.min(100, Math.round(((data.downloaded ?? 0) / data.contentLength) * 100))
                : null;
            showCard({ kind: "downloading", percent });
            break;
          }
          case "Finished":
            showCard({ kind: "installing" });
            break;
        }
      });
      // Windows: the updater exits the app here to launch the installer.
    } catch (error) {
      busy = false;
      console.error("KeyPulse update install failed:", error);
      showCard({ kind: "error", message: errorMessage(error) });
    }
  } else if (action === "later") {
    localStorage.setItem(DISMISSED_KEY, current.version);
    showCard({ kind: "hidden" });
  } else if (action === "retry") {
    showCard({ kind: "hidden" });
    void checkForUpdate(true);
  } else if (action === "close") {
    showCard({ kind: "hidden" });
  }
}

function currentIsHidden(): boolean {
  return view.kind === "hidden";
}

function showCard(next: View): void {
  view = next;
  const root = ensureCard();
  if (next.kind === "hidden") {
    root.classList.add("kp-updater--hidden");
    return;
  }
  root.classList.remove("kp-updater--hidden");
  root.replaceChildren(buildContent(next));
}

function buildContent(next: View): HTMLElement {
  const panel = document.createElement("div");
  panel.className = "kp-updater__panel";

  const title = document.createElement("div");
  title.className = "kp-updater__title";
  const body = document.createElement("div");
  body.className = "kp-updater__body";

  if (next.kind === "hidden") {
    return panel; // never rendered; showCard hides the root instead
  } else if (next.kind === "found") {
    title.textContent = `发现新版本 v${next.version}`;
    body.textContent = "可一键安装更新，应用会自动重启。";
    panel.append(title, body, buttonRow([{ action: "install", label: "立即更新", primary: true }, { action: "later", label: "稍后" }]));
  } else if (next.kind === "downloading") {
    title.textContent = `正在下载 v${current?.version ?? ""}`;
    body.textContent =
      next.percent === null ? "首次下载可能需要一点时间，请稍候…" : `已下载 ${next.percent}%，下载完成后会自动安装。`;
    const track = document.createElement("div");
    track.className = "kp-updater__track";
    const bar = document.createElement("div");
    bar.className = next.percent === null ? "kp-updater__bar kp-updater__bar--indeterminate" : "kp-updater__bar";
    if (next.percent !== null) bar.style.width = `${next.percent}%`;
    track.appendChild(bar);
    panel.append(title, body, track);
  } else if (next.kind === "installing") {
    title.textContent = "正在安装更新";
    body.textContent = "应用即将自动重启，请稍候…";
    panel.append(title, body);
  } else {
    title.textContent = "检查更新失败";
    body.textContent = next.message;
    panel.append(title, body, buttonRow([{ action: "retry", label: "重试", primary: true }, { action: "close", label: "关闭" }]));
  }
  return panel;
}

function buttonRow(buttons: Array<{ action: string; label: string; primary?: boolean }>): HTMLElement {
  const row = document.createElement("div");
  row.className = "kp-updater__actions";
  for (const config of buttons) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.action = config.action;
    button.className = config.primary ? "kp-updater__btn kp-updater__btn--primary" : "kp-updater__btn";
    button.textContent = config.label;
    row.appendChild(button);
  }
  return row;
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

// ============================= styles =============================

const STYLE_ID = "kp-updater-style";

function injectStyles(): void {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
.kp-updater {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 2147483000;
  font-family: "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
}
.kp-updater--hidden { display: none; }
.kp-updater__panel {
  width: 292px;
  box-sizing: border-box;
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(26, 28, 34, 0.95);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
  color: #eef1f4;
  font-size: 13px;
  line-height: 1.55;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.kp-updater__title { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.kp-updater__body { color: #b9c0ca; margin-bottom: 10px; word-break: break-word; }
.kp-updater__actions { display: flex; gap: 8px; justify-content: flex-end; }
.kp-updater__btn {
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: transparent;
  color: #d7dce2;
  border-radius: 7px;
  padding: 5px 14px;
  font-size: 12.5px;
  cursor: pointer;
}
.kp-updater__btn:hover { background: rgba(255, 255, 255, 0.08); }
.kp-updater__btn--primary {
  border: none;
  background: #7ba889;
  color: #16201a;
  font-weight: 600;
}
.kp-updater__btn--primary:hover { background: #8fb99c; }
.kp-updater__track {
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}
.kp-updater__bar {
  height: 100%;
  border-radius: 3px;
  background: #7ba889;
  transition: width 0.2s ease;
}
.kp-updater__bar--indeterminate {
  width: 40%;
  animation: kp-updater-slide 1.2s ease-in-out infinite;
}
@keyframes kp-updater-slide {
  0% { transform: translateX(-110%); }
  100% { transform: translateX(360%); }
}`;
  document.head.appendChild(style);
}

injectStyles();
