"""CDP helper: evaluate JS in the KeyPulse WebView2 page and print the result."""
import asyncio
import json
import sys
import urllib.request

import websockets


def get_page_ws_url(port=9222):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    for target in targets:
        if target.get("type") == "page" and "webSocketDebuggerUrl" in target:
            return target["webSocketDebuggerUrl"], target.get("title", ""), target.get("url", "")
    raise RuntimeError(f"no page target found: {targets}")


def get_target_ws_url(port=9222, index=0):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages or index >= len(pages):
        raise RuntimeError(f"page target {index} not found; have {len(pages)}")
    target = pages[index]
    return target["webSocketDebuggerUrl"], target.get("title", ""), target.get("url", "")


async def evaluate(expr, port=9222, await_promise=True, target_index=0):
    ws_url, title, url = get_target_ws_url(port, target_index)
    async with websockets.connect(ws_url, max_size=16 * 1024 * 1024) as ws:
        await ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expr,
                "returnByValue": True,
                "awaitPromise": await_promise,
            },
        }))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                if "error" in msg:
                    return {"error": msg["error"]}
                result = msg.get("result", {}).get("result", {})
                if result.get("subtype") == "error":
                    return {"error": result.get("description")}
                return {"value": result.get("value")}


def main():
    if len(sys.argv) < 2:
        print("usage: cdp_eval.py <js-expression-file-or-inline>")
        return 2
    arg = sys.argv[1]
    target_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if arg.startswith("@"):
        with open(arg[1:], encoding="utf-8") as fh:
            expr = fh.read()
    else:
        expr = arg
    out = asyncio.run(evaluate(expr, target_index=target_index))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if "error" not in out else 1


if __name__ == "__main__":
    sys.exit(main())
