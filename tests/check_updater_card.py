"""Poll all CDP page targets for the updater card and print its text."""
import asyncio
import sys
import urllib.request
import json

sys.path.insert(0, "tests")
from cdp_eval import evaluate  # noqa: E402

EXPR = (
    "JSON.stringify({"
    "card: !!document.querySelector('.kp-updater'),"
    "hidden: document.querySelector('.kp-updater--hidden') !== null,"
    "text: (document.querySelector('.kp-updater__panel')?.textContent || '').trim(),"
    "btns: Array.from(document.querySelectorAll('.kp-updater__btn')).map(b => b.textContent)"
    "})"
)


def page_urls():
    with urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    return [t for t in targets if t.get("type") == "page"]


async def main():
    for attempt in range(10):
        pages = page_urls()
        results = []
        for index in range(len(pages)):
            try:
                raw = await evaluate(EXPR, target_index=index)
                results.append((index, raw))
            except Exception as error:  # noqa: BLE001
                results.append((index, f"ERR {error}"))
        for index, raw in results:
            if isinstance(raw, str) and '"card":true' in raw.replace(" ", ""):
                print(f"[attempt {attempt}] target {index}: {raw}")
                return
        print(f"[attempt {attempt}] no card yet: {results}")
        await asyncio.sleep(2)
    print("UPDATER CARD NOT FOUND within timeout")


asyncio.run(main())
