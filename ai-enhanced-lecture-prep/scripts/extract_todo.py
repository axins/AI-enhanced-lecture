#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽取讲稿中的「待核实」条目，生成带页号定位的核查清单。

用法：
    python extract_todo.py --dir . --out verify_list.md
    python extract_todo.py --dir . --glob "*讲稿*.md"
    python extract_todo.py --dir . --markers 需核实,待核实,存疑
"""
import argparse
import glob
import io
import os
import re
import sys

DEFAULT_MARKERS = ["需核实", "待核实", "待查", "存疑", "未核实", "出处待核实"]


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def find_page(text, pos):
    idx = text.rfind("\n## 第 ", 0, pos)
    if idx == -1:
        return "?"
    m = re.match(r"\n## 第 (\d+) 页", text[idx:])
    return m.group(1) if m else "?"


def expand_item(text, start, end):
    """从标记所在行向前扩展，取回完整的列表条目。"""
    ctx = text.rfind("\n", 0, start) + 1
    for _ in range(6):
        prev = text.rfind("\n", 0, ctx - 1) + 1
        prev_line = text[prev:ctx].strip()
        if prev_line.startswith(("- ", "  - ", "> ", "| ", "【")):
            ctx = prev
        else:
            break
    return " ".join(text[ctx:end].split())


def main():
    _utf8()
    ap = argparse.ArgumentParser(description="待核实条目抽取")
    ap.add_argument("--dir", default=".", help="课程目录")
    ap.add_argument("--glob", default="*.md", help="文件匹配模式")
    ap.add_argument("--out", default="verify_list.md", help="输出清单")
    ap.add_argument("--markers", default="", help="标记词，逗号分隔")
    a = ap.parse_args()

    markers = [m.strip() for m in a.markers.split(",") if m.strip()] or DEFAULT_MARKERS
    files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
    if not files:
        print("未匹配到任何文件：%s" % os.path.join(a.dir, a.glob))
        return 1

    buf = ["# 讲稿「待核实」条目核查清单\n",
           "> 由 `extract_todo.py` 自动生成。核查完成后须回写讲稿并删除标记；\n",
           "> 检索不到的条目改写为「未检索到权威来源，建议课堂上不引用」。\n"]
    total, per_file = 0, []
    for f in files:
        text = io.open(f, encoding="utf-8").read()
        rows = []
        for m in re.finditer("|".join(re.escape(x) for x in markers), text):
            end = text.find("\n", m.start())
            if end == -1:
                end = len(text)
            rows.append((find_page(text, m.start()), expand_item(text, m.start(), end)))
        if not rows:
            continue
        name = os.path.basename(f)
        per_file.append((name, len(rows)))
        total += len(rows)
        buf.append("\n## %s（%d 处）\n" % (name, len(rows)))
        last = None
        for page, item in rows:
            if page != last:
                buf.append("\n### 第 %s 页\n" % page)
                last = page
            buf.append("- [ ] %s\n" % item[:220])

    buf.insert(3, "\n合计 %d 处；分布：%s\n" % (
        total, "、".join("%s %d" % (n, c) for n, c in per_file)))
    io.open(a.out, "w", encoding="utf-8").write("".join(buf))
    print("已写入 %s，合计 %d 处" % (a.out, total))
    for n, c in per_file:
        print("  %-42s %d" % (n, c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
