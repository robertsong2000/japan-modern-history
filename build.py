#!/usr/bin/env python3
"""Build a static Chinese reader from translated Markdown."""

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKS = ROOT / "works"
SITE = ROOT / "site"

YEAR = {
    "senchu": 1867,
    "hassaku": 1867,
    "kaien": 1867,
    "nakae": 1881,
    "kawai": 1936,
    "naito": 1922,
    "yoshino": 1916,
    "katsu-taisei": 1898,
    "katsu-hatamoto": 1898,
    "katsu-ryokan": 1898,
    "katsu-mokumoku": 1898,
    "fukuzawa": 1875,
    "takekoshi": 1895,
    "komoto": 1954,
    "maeda": 1946,
    "tsurezure": 1331,
    "saikaku-fuko": 1686,
}


def parse_md(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise SystemExit(f"missing front matter: {path}")
    _, meta, body = text.split("---", 2)
    data = {}
    for line in meta.strip().splitlines():
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    data["body"] = body.strip()
    data["year"] = YEAR[data["id"]]
    data["file"] = path.name
    return data


def body_html(body: str) -> str:
    parts = []
    headings = []
    n = 0
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block:
            continue
        if block.startswith("## "):
            n += 1
            title = block[3:].strip()
            slug = f"s{n}"
            headings.append((slug, title))
            parts.append(f'<h2 id="{slug}">{html.escape(title)}</h2>')
            continue
        lines = [html.escape(line.strip()) for line in block.splitlines() if line.strip()]
        parts.append("<p>" + "<br>\n".join(lines) + "</p>")
    html_body = "\n".join(parts)
    if len(headings) < 12:
        return html_body
    links = "".join(
        f'<a href="#{slug}">{html.escape(title)}</a>' for slug, title in headings
    )
    return f'<nav class="toc" aria-label="段目">{links}</nav>\n{html_body}'


CSS = """
:root {
  --paper: #f4ecdc;
  --ink: #1b1612;
  --muted: #6d6256;
  --line: #d9cbb6;
  --card: #fbf7ef;
  --seal: #8e2f2a;
  --moss: #2f463c;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--ink);
  background:
    radial-gradient(1200px 500px at 10% -10%, #fffaf1 0%, transparent 50%),
    var(--paper);
  font-family: "Iowan Old Style", Palatino, "Songti SC", "Noto Serif SC", "Source Han Serif SC", serif;
  line-height: 1.9;
}
a { color: var(--seal); text-decoration-thickness: 1px; text-underline-offset: 0.18em; }
.wrap { width: min(760px, calc(100% - 40px)); margin: 0 auto; }
header.site {
  border-bottom: 1px solid var(--line);
  padding: 28px 0 22px;
}
.mark {
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-right: 8px;
  border: 1.5px solid var(--seal);
  border-radius: 2px;
  vertical-align: -1px;
}
.kicker {
  letter-spacing: 0.18em;
  font-size: 12px;
  color: var(--seal);
  margin: 0 0 8px;
}
h1 { font-weight: 560; font-size: 34px; line-height: 1.25; margin: 0; }
.lede { color: var(--muted); margin: 12px 0 0; font-size: 17px; }
.era {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 0.14em;
  color: var(--moss);
  border: 1px solid var(--line);
  padding: 0 8px;
  border-radius: 99px;
  margin-right: 8px;
}
ol.index { list-style: none; padding: 8px 0 64px; margin: 0; }
ol.index li {
  border-top: 1px solid var(--line);
  padding: 18px 0;
}
ol.index a.title {
  color: var(--ink);
  text-decoration: none;
  font-size: 22px;
}
ol.index a.title:hover { color: var(--seal); }
.meta { color: var(--muted); font-size: 14px; margin-top: 4px; }
article { padding: 28px 0 80px; }
article h1 { font-size: 36px; }
article h2 {
  font-size: 18px;
  font-weight: 560;
  margin: 2.2em 0 0.6em;
  color: var(--moss);
}
nav.toc {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  margin: 22px 0 8px;
  padding: 12px 0 4px;
  border-top: 1px solid var(--line);
}
nav.toc a {
  color: var(--moss);
  font-size: 13px;
  text-decoration: none;
}
nav.toc a:hover { color: var(--seal); }
.note {
  background: var(--card);
  border-left: 3px solid var(--seal);
  padding: 12px 16px;
  color: #3c332c;
  font-size: 16px;
}
article p { font-size: 18px; margin: 0 0 1.05em; }
.back { font-size: 14px; letter-spacing: 0.08em; }
footer {
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 13px;
  padding: 18px 0 40px;
}
"""


def page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def main() -> None:
    SITE.mkdir(exist_ok=True)
    works = [parse_md(p) for p in sorted(WORKS.glob("*.md"))]
    works.sort(key=lambda w: (w["year"], w["file"]))
    items = []
    for w in works:
        href = f"{w['id']}.html"
        items.append(
            "<li>"
            f"<span class=\"era\">{html.escape(w['era'])}</span>"
            f"<a class=\"title\" href=\"{href}\">{html.escape(w['title'])}</a>"
            f"<div class=\"meta\">{html.escape(w['author'])} · {html.escape(w['date'])}</div>"
            "</li>"
        )
    index = page(
        "公版日本近代史料",
        f"""
<header class="site"><div class="wrap">
<p class="kicker"><span class="mark"></span>青空文库 · 中文译读</p>
<h1>公版日本近代史料</h1>
<p class="lede">版权已经届满、可以在青空文库直接下载 TXT 的文本。这里是中文译文。原文不在这几页里重贴，链接回到青空文库。</p>
</div></header>
<main class="wrap"><ol class="index">
{''.join(items)}
</ol></main>
<footer><div class="wrap">译文据青空文库文本译出。青空文库的输入与校对由志愿者完成。</div></footer>
""",
    )
    (SITE / "index.html").write_text(index, encoding="utf-8")
    for w in works:
        article = page(
            f"{w['title']} · {w['author']}",
            f"""
<header class="site"><div class="wrap">
<p class="back"><a href="index.html">目录</a></p>
<p class="kicker"><span class="era">{html.escape(w['era'])}</span>{html.escape(w['date'])}</p>
<h1>{html.escape(w['title'])}</h1>
<p class="lede">{html.escape(w['author'])}</p>
</div></header>
<main class="wrap"><article>
<p class="note">{html.escape(w['headnote'])}</p>
{body_html(w['body'])}
</article></main>
<footer><div class="wrap">底本：{html.escape(w['source'])}。 <a href="{html.escape(w['url'])}">青空文库图书卡</a></div></footer>
""",
        )
        (SITE / f"{w['id']}.html").write_text(article, encoding="utf-8")
    print(f"wrote {len(works)} works")


if __name__ == "__main__":
    main()
