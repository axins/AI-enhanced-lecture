#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出课件(.pptx)的页序索引；可选导出指定页全文与备注。

v3 变更：
- 解析结果进缓存，同一课件后续调用直接命中（不再重复解析）
- .ppt 等旧格式明确报错并给出另存指令，退出码 2
- 新增 --json（供下游脚本/批处理消费）、--timing、--version
- --pages 支持区间写法（1-9）

用法：
    python deck_index.py <deck.pptx>                  # 页序索引（表格）
    python deck_index.py <deck.pptx> --pages 1,2,5    # 指定页全文 + 备注
    python deck_index.py <deck.pptx> --pages 3-9      # 区间
    python deck_index.py <deck.pptx> --out index.md   # 写入文件
    python deck_index.py <deck.pptx> --json index.json
"""
import argparse
import io
import json
import sys
import time

import _deck

VERSION = "3.0"
DEFAULT = "（本页无文字）"


def parse_pages(spec, total):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                out.extend(range(int(a), int(b) + 1))
            except ValueError:
                continue
        else:
            try:
                out.append(int(part))
            except ValueError:
                continue
    return [i for i in out if 1 <= i <= total]


def cell(text, limit=40):
    t = " ".join(text.split())
    if not t:
        return DEFAULT
    return t[:limit].replace("|", "/")


def main():
    _deck.utf8_stdout()
    ap = argparse.ArgumentParser(description="课件页序索引导出")
    ap.add_argument("deck", help="课件 .pptx 路径")
    ap.add_argument("--pages", default="", help="仅导出这些页的全文，如 1,2,5 或 3-9")
    ap.add_argument("--out", default="", help="输出文件（默认打印到标准输出）")
    ap.add_argument("--json", default="", help="页序索引的 JSON 输出路径")
    ap.add_argument("--no-cache", action="store_true", help="不读写解析缓存")
    ap.add_argument("--timing", action="store_true", help="输出解析耗时到标准错误")
    ap.add_argument("--version", action="version", version="deck_index.py " + VERSION)
    a = ap.parse_args()

    t0 = time.time()
    try:
        deck = _deck.load_deck(a.deck, use_cache=not a.no_cache)
    except _deck.DeckError as e:
        return _deck.fail(str(e))
    slides = deck["pages"]
    cost = time.time() - t0
    if a.timing:
        sys.stderr.write("[timing] 解析 %.2fs（%s，共 %d 页）\n"
                         % (cost, "缓存命中" if deck["cached"] else "首次解析", len(slides)))

    lines = []
    if a.pages:
        for i in parse_pages(a.pages, len(slides)):
            s = slides[i - 1]
            lines.append("===== 第 %d 页（版式：%s） =====" % (i, s["layout"]))
            lines.append(s["text"] if s["text"].strip() else DEFAULT)
            if s["notes"]:
                lines.append("--- 备注 ---")
                lines.append(s["notes"])
            lines.append("")
    else:
        lines.append("总页数：%d" % len(slides))
        lines.append("")
        lines.append("| 页号 | 版式 | 首行文本 |")
        lines.append("|---|---|---|")
        for s in slides:
            lines.append("| %d | %s | %s |" % (s["n"], s["layout"], cell(s["text"])))
        blank = [str(s["n"]) for s in slides if s["blank"]]
        if blank:
            lines.append("")
            lines.append("无文字页（图片页/空白页）：%s" % ", ".join(blank))

    out = "\n".join(lines)
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(out + "\n")
        print("已写入 %s" % a.out)
    else:
        print(out)

    if a.json:
        payload = {
            "deck": a.deck,
            "total": len(slides),
            "cached": deck["cached"],
            "pages": slides,
            "blank_pages": [s["n"] for s in slides if s["blank"]],
        }
        io.open(a.json, "w", encoding="utf-8").write(
            json.dumps(payload, ensure_ascii=False, indent=2))
        print("JSON 已写入 %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
