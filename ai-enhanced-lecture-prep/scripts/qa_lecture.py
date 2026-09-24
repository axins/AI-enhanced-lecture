#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""讲稿质检：页序覆盖、重复、顺序、维度计数、空白页、标记词、交叉引用、链接。

用法：
    python qa_lecture.py <讲稿.md>                      # 按最大页号推断应有页数
    python qa_lecture.py <讲稿.md> --expect 52          # 指定应有页数
    python qa_lecture.py <讲稿.md> --deck <deck.pptx>   # 与课件页数比对
    python qa_lecture.py <讲稿.md> --dimensions 理论,人物,案例,文献,实践,互动
"""
import argparse
import io
import os
import re
import sys

DEFAULT_DIMENSIONS = ["理论", "人物", "案例", "文献", "实践", "互动"]
DEFAULT_MARKERS = ["需核实", "待核实", "待查", "存疑", "未核实"]
LINK_TYPES = ["数据库DOI", "开放获取", "官方一手", "媒体报道", "判例数据"]
BLOCKS = ["【历史脉络】", "【逻辑关联】", "【参考链接】"]


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def deck_pages(path):
    try:
        from pptx import Presentation
    except ImportError:
        print("提示：未安装 python-pptx，跳过与课件的页数比对（pip install python-pptx）")
        return None
    return len(Presentation(path).slides)


def main():
    _utf8()
    ap = argparse.ArgumentParser(description="讲稿质检")
    ap.add_argument("notes", help="讲稿 .md 路径")
    ap.add_argument("--expect", type=int, default=0, help="应有页数")
    ap.add_argument("--deck", default="", help="课件 .pptx，用于比对页数")
    ap.add_argument("--dimensions", default="", help="标注维度，逗号分隔")
    ap.add_argument("--markers", default="", help="待核实标记词，逗号分隔")
    ap.add_argument("--min-refs", type=int, default=3, help="最少交叉引用数（默认 3）")
    a = ap.parse_args()

    dims = [d.strip() for d in a.dimensions.split(",") if d.strip()] or DEFAULT_DIMENSIONS
    markers = [m.strip() for m in a.markers.split(",") if m.strip()] or DEFAULT_MARKERS

    text = io.open(a.notes, encoding="utf-8").read()
    pages = [int(m.group(1)) for m in re.finditer(r"^## 第 (\d+) 页", text, re.M)]

    expect = a.expect
    if a.deck and os.path.exists(a.deck):
        n = deck_pages(a.deck)
        if n:
            expect = n
    if not expect:
        expect = max(pages) if pages else 0

    problems = []
    missing = [i for i in range(1, expect + 1) if i not in pages]
    dup = sorted({p for p in pages if pages.count(p) > 1})
    if missing:
        problems.append("缺页：%s" % missing)
    if dup:
        problems.append("重复页：%s" % dup)
    if pages != sorted(pages):
        problems.append("页号未递增：%s" % pages[:12])
    if expect and len(pages) != expect:
        problems.append("页数不符：%d（应为 %d）" % (len(pages), expect))

    # 空白页是否显式标注
    for m in re.finditer(r"^## 第 (\d+) 页(.*)$", text, re.M):
        if "空白页" in m.group(2) or "无文字" in m.group(2):
            seg = text[m.end():m.end() + 400]
            if "需补充" not in seg and "◤" not in seg:
                problems.append("第 %s 页（空白页）未给出处理建议" % m.group(1))

    # 维度计数
    counts = {d: len(re.findall("◤%s◢" % d, text)) for d in dims}
    for d in dims:
        if counts[d] == 0:
            problems.append("维度缺失：◤%s◢" % d)
    total_dim = sum(counts.values()) or 1
    for d, c in counts.items():
        if c / total_dim > 0.6:
            problems.append("维度失衡：◤%s◢ 占比 %.0f%%" % (d, 100 * c / total_dim))

    # 标记词
    marks = sum(len(re.findall(re.escape(m), text)) for m in markers)

    # 交叉引用
    refs = len(re.findall(r"回接\s*第?\s*\d+\s*讲", text)) + len(re.findall(r"回接\s*L\d+", text))
    if refs < a.min_refs:
        problems.append("交叉引用不足：%d 条（建议 ≥%d）" % (refs, a.min_refs))

    # 链接
    urls = len(re.findall(r"https?://", text))
    typed = {t: len(re.findall(r"\[%s\]" % t, text)) for t in LINK_TYPES}
    blocks = {b: text.count(b) for b in BLOCKS}

    print("文件：%s" % os.path.basename(a.notes))
    print("字数：%d　页：%d（应 %d）　链接：%d" % (len(text), len(pages), expect, urls))
    print("维度：" + "　".join("◤%s◢ %d" % (d, counts[d]) for d in dims))
    print("链接类型：" + "　".join("%s %d" % (t, typed[t]) for t in LINK_TYPES))
    print("三子块：" + "　".join("%s %d" % (b, blocks[b]) for b in BLOCKS))
    print("交叉引用：%d 条　待核实标记：%d 处" % (refs, marks))
    print()
    if problems:
        print("===== 质检未通过（%d 项）=====" % len(problems))
        for p in problems:
            print("[问题] " + p)
        return 1
    print("===== 质检通过 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
