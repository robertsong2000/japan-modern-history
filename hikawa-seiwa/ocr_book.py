#!/usr/bin/env python3
"""OCR the 1933 Daibunkan scan of Hikawa Seiwa from NDL IIIF images."""

import io
import os
import subprocess
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
PAGE_DIR = ROOT / "pages"
TEXT_DIR = ROOT / "text" / "pages"
TESS = "/opt/homebrew/Cellar/tesseract/5.5.3/bin/tesseract"
TESSDATA = ROOT / "tessdata"
IIIF = "https://dl.ndl.go.jp/api/iiif/1904401/R{n:07d}/full/full/0/default.jpg"
N_PAGES = 214
UA = "hikawa-seiwa-reader/1.0 (local research transcription)"


def download(n: int) -> Path:
    dest = PAGE_DIR / f"{n:04d}.jpg"
    if dest.exists() and dest.stat().st_size > 10000:
        return dest
    url = IIIF.format(n=n)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return dest


def text_columns(gray: np.ndarray):
    h, w = gray.shape
    # Drop the photo surround and the running header band.
    a = gray[int(h * 0.07) : int(h * 0.94), int(w * 0.05) : int(w * 0.95)]
    ink = a < 95
    col = ink.sum(axis=0)
    gap = col < 5
    runs = []
    state = None
    for i, is_gap in enumerate(gap):
        st = "g" if is_gap else "i"
        if st != state:
            runs.append([st, i, 1])
            state = st
        else:
            runs[-1][2] += 1
    merged = []
    for st, start, length in runs:
        if merged and st == "g" and length < 10:
            merged[-1][2] += length
            continue
        if merged and st == "i" and merged[-1][0] == "i":
            merged[-1][2] += length
            continue
        merged.append([st, start, length])
    cols = [(s, s + length) for st, s, length in merged if st == "i" and length > 36]
    # Right-to-left reading order.
    strips = []
    for x0, x1 in reversed(cols):
        pad = 4
        strips.append(a[:, max(0, x0 - pad) : min(a.shape[1], x1 + pad)])
    return strips


def ocr_strip(strip: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(strip).save(buf, format="PNG")
    env = os.environ.copy()
    env["TESSDATA_PREFIX"] = str(TESSDATA)
    proc = subprocess.run(
        [TESS, "stdin", "stdout", "-l", "jpn_vert", "--psm", "5", "-c", "preserve_interword_spaces=0"],
        input=buf.getvalue(),
        capture_output=True,
        env=env,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.decode("utf-8", "replace").strip()


def ocr_half(gray: np.ndarray) -> str:
    parts = []
    for strip in text_columns(gray):
        # Skip tiny header crumbs and furigana-only slivers.
        if strip.shape[1] < 40 or strip.shape[0] < 200:
            continue
        text = ocr_strip(strip)
        text = " ".join(text.split())
        if len(text) < 8:
            continue
        parts.append(text)
    return "\n".join(parts)


def ocr_spread(path: Path) -> str:
    im = Image.open(path).convert("L")
    arr = np.array(im)
    h, w = arr.shape
    mid = w // 2
    # Open book: read the right page first, then the left page.
    right = ocr_half(arr[:, mid:])
    left = ocr_half(arr[:, :mid])
    blocks = [b for b in (right, left) if b]
    return "\n\n".join(blocks)


def work(n: int) -> tuple[int, int]:
    path = download(n)
    out = TEXT_DIR / f"{n:04d}.txt"
    if out.exists() and out.stat().st_size > 20:
        return n, out.stat().st_size
    text = ocr_spread(path)
    out.write_text(text + "\n", encoding="utf-8")
    return n, len(text)


def main():
    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    done = 0
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(work, n) for n in range(1, N_PAGES + 1)]
        for fut in as_completed(futures):
            n, size = fut.result()
            done += 1
            print(f"{done}/{N_PAGES} page {n:04d} chars {size}", flush=True)


if __name__ == "__main__":
    main()
