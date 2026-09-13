"""Open the three reworked UI surfaces via CDP and screenshot each."""
import asyncio
import base64
import json
import sys
import urllib.request

import websockets


def find_main_target():
    with urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    pages = [t for t in targets if t.get("type") == "page"]
    for t in pages:
        ws = t.get("webSocketDebuggerUrl")
        if not ws:
            continue
        return ws, t.get("title", "")
    raise RuntimeError("no page target")


async def main():
    with urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=5) as resp:
        targets = [t for t in json.loads(resp.read().decode()) if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    ws_url = None
    for t in targets:
        async with websockets.connect(t["webSocketDebuggerUrl"], max_size=20 * 1024 * 1024) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": "!!document.querySelector('.avatar-button') && !!document.querySelector('.topbar-actions')", "returnByValue": True}}))
            msg = json.loads(await ws.recv())
            if msg.get("result", {}).get("result", {}).get("value"):
                ws_url = t["webSocketDebuggerUrl"]
                break
    if not ws_url:
        raise RuntimeError("main window target not found")
    async with websockets.connect(ws_url, max_size=20 * 1024 * 1024) as ws:
        mid = 0

        async def call(method, params=None):
            nonlocal mid
            mid += 1
            await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == mid:
                    return msg

        async def shot(name):
            nonlocal mid
            mid += 1
            await ws.send(json.dumps({"id": mid, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == mid:
                    data = base64.b64decode(msg["result"]["data"])
                    path = rf"C:\Users\579\AppData\Local\Temp\ui-{name}.png"
                    open(path, "wb").write(data)
                    print("saved", path)
                    return

        async def click(js, wait=1.2):
            await call("Runtime.evaluate", {"expression": js, "awaitPromise": True})
            await asyncio.sleep(wait)

        await asyncio.sleep(1)
        # 1. account popover
        await click("document.querySelector('.avatar-button')?.click()")
        await shot("account")
        # 2. privacy dialog
        await click("[...document.querySelectorAll('.account-btn')].find(b => b.textContent.includes('隐私'))?.click()", 1.5)
        await shot("privacy")
        # 3. login portal (privacy close also closed the popover → reopen)
        await click("document.querySelector('.privacy-close')?.click()", 0.6)
        await click("document.querySelector('.avatar-button')?.click()", 0.8)
        await click("[...document.querySelectorAll('.account-btn')].find(b => b.textContent.includes('登录'))?.click()", 2.0)
        await shot("portal")
        # state snapshot for sanity
        r = await call("Runtime.evaluate", {"expression": "JSON.stringify({avatar: document.querySelector('.avatar-button')?.textContent?.trim()})", "returnByValue": True})
        print("state:", r.get("result", {}).get("result", {}).get("value"))


asyncio.run(main())
