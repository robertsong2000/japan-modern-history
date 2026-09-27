#!/usr/bin/env python3
"""Turn NDL OCR JSON into flowing Japanese text and a Chinese machine translation."""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NDL = ROOT / "text" / "ndl"
OUT = ROOT / "text"
N_PAGES = 214


def page_text(n: int) -> str:
    path = NDL / f"1904401_{n:07d}.json"
    if not path.exists():
        return ""
    items = json.loads(path.read_text(encoding="utf-8"))
    kept = []
    for it in items:
        text = (it.get("contenttext") or "").strip()
        if not text:
            continue
        width = it["xmax"] - it["xmin"]
        height = it["ymax"] - it["ymin"]
        # Drop furigana columns. Main type is roughly 60px and wider.
        if width < 55 or height < 70:
            continue
        it = dict(it)
        it["cx"] = (it["xmin"] + it["xmax"]) / 2
        it["text"] = text
        kept.append(it)
    kept.sort(key=lambda it: -it["cx"])
    columns = []
    for it in kept:
        if columns and abs(it["cx"] - columns[-1][0]["cx"]) < 28:
            columns[-1].append(it)
        else:
            columns.append([it])
    parts = []
    for col in columns:
        col.sort(key=lambda it: it["ymin"])
        piece = "".join(it["text"] for it in col)
        piece = piece.replace("氷川清話", "").replace("海舟先生", "").strip()
        if len(piece) < 2:
            continue
        parts.append(piece)
    raw = "".join(parts)
    raw = raw.replace("〓", "□")
    # One sentence a line, so the reader can scan.
    raw = raw.replace("。", "。\n")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    return "\n".join(lines)


def translate(text: str) -> str:
    chunks = []
    buf = ""
    for line in text.splitlines():
        if len(buf) + len(line) > 700:
            if buf:
                chunks.append(buf)
            buf = line
        else:
            buf = (buf + "\n" + line).strip()
    if buf:
        chunks.append(buf)
    out = []
    for chunk in chunks:
        out.append(translate_chunk(chunk))
        time.sleep(0.25)
    return "\n".join(out)


def translate_chunk(text: str) -> str:
    url = (
        "https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=ja&tl=zh-CN&q="
        + urllib.parse.quote(text)
    )
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                return "".join(str(x) for x in data)
            if isinstance(data, str):
                return data
            return str(data)
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    return f"〔这页翻译没有成功：{last}〕\n{text}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pages = []
    for n in range(1, N_PAGES + 1):
        ja = page_text(n)
        if len(ja) < 40:
            continue
        pages.append({"n": n, "ja": ja})
    ja_md = ["# 海舟先生氷川清話", "", "勝海舟 述 / 吉本襄 撰。底本：大文館書店、1933年。", ""]
    for page in pages:
        ja_md.append(f"## 第{page['n']}葉")
        ja_md.append("")
        ja_md.append(page["ja"])
        ja_md.append("")
    ja_path = OUT / "hikawa.md"
    ja_txt = OUT / "hikawa.txt"
    body = "\n".join(ja_md)
    ja_path.write_text(body, encoding="utf-8")
    ja_txt.write_text("\n\n".join(p["ja"] for p in pages), encoding="utf-8")
    print(f"japanese pages {len(pages)} chars {sum(len(p['ja']) for p in pages)}", flush=True)

    cache_path = OUT / "pages.json"
    cache = {}
    if cache_path.exists():
        cache = {item["n"]: item for item in json.loads(cache_path.read_text(encoding="utf-8"))}
    done = []
    for i, page in enumerate(pages, 1):
        cached = cache.get(page["n"])
        if cached and cached.get("zh") and "翻译没有成功" not in cached["zh"]:
            page["zh"] = cached["zh"]
        else:
            page["zh"] = translate(page["ja"])
        done.append(page)
        cache_path.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
        print(f"translated {i}/{len(pages)} leaf {page['n']}", flush=True)

    zh_md = ["# 冰川清话", "", "胜海舟口述，吉本襄编。据1933年大文馆书店本的公开扫描识别后译出。", ""]
    for page in done:
        zh_md.append(f"## 第{page['n']}叶")
        zh_md.append("")
        zh_md.append(page["zh"])
        zh_md.append("")
    (OUT / "hikawa-zh.md").write_text("\n".join(zh_md), encoding="utf-8")
    print("wrote markdown", flush=True)


if __name__ == "__main__":
    main()
