#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全课程讲稿进度报告：字数、链接、类型分布、三子块覆盖、待核实残留。

用法：
    python progress_report.py --dir .
    python progress_report.py --dir . --glob "*讲稿与教案.md"
"""
import argparse
import glob
import io
import os
import re
import sys

LINK_TYPES = ["数据库DOI", "开放获取", "官方一手", "媒体报道", "判例数据"]
BLOCKS = ["【历史脉络】", "【逻辑关联】", "【参考链接】"]
MARKERS = ["需核实", "待核实", "待查", "存疑", "未核实"]


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def short(name):
    return name.replace(".md", "")


def main():
    _utf8()
    ap = argparse.ArgumentParser(description="讲稿进度报告")
    ap.add_argument("--dir", default=".", help="课程目录")
    ap.add_argument("--glob", default="*.md", help="文件匹配模式")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
    if not files:
        print("未匹配到任何文件：%s" % os.path.join(a.dir, a.glob))
        return 1

    hdr = ("%-22s" % "文件") + "".join("%7s" % h for h in
          ["字数", "链接", "DOI", "开放", "官方", "媒体", "判例", "待核"])
    print(hdr)
    print("-" * len(hdr.expandtabs()))
    tot = dict((t, 0) for t in LINK_TYPES)
    t_char = t_link = t_ver = 0
    t_blocks = dict((b, 0) for b in BLOCKS)
    for f in files:
        t = io.open(f, encoding="utf-8").read()
        n = len(re.findall(r"https?://", t))
        cs = [len(re.findall(r"\[%s\]" % k, t)) for k in LINK_TYPES]
        ver = sum(len(re.findall(re.escape(m), t)) for m in MARKERS)
        bs = [t.count(b) for b in BLOCKS]
        print(("%-22s" % short(os.path.basename(f))[:22]) +
              ("%7d" % len(t)) + ("%7d" % n) +
              "".join("%7d" % c for c in cs) + ("%7d" % ver))
        for k, c in zip(LINK_TYPES, cs):
            tot[k] += c
        for b, c in zip(BLOCKS, bs):
            t_blocks[b] += c
        t_char += len(t)
        t_link += n
        t_ver += ver
    print("-" * 80)
    print(("%-22s" % "合计") + ("%7d" % t_char) + ("%7d" % t_link) +
          "".join("%7d" % tot[k] for k in LINK_TYPES) + ("%7d" % t_ver))
    print("\n三子块合计：" + "　".join("%s %d" % (b, t_blocks[b]) for b in BLOCKS))

    # 危险信号
    warn = []
    for f in files:
        t = io.open(f, encoding="utf-8").read()
        name = os.path.basename(f)
        if t.count("http") > 5 and not any(("[%s]" % k) in t for k in LINK_TYPES):
            warn.append("%s：链接多但无类型标签，可能是堆砌" % name)
        if len(re.findall(r"https?://", t)) == 0 and len(t) > 20000:
            warn.append("%s：字数可观但无外部链接" % name)
        if not re.search(r"回接\s*第?\s*\d+\s*讲", t) and not re.search(r"回接\s*L\d+", t):
            warn.append("%s：无跨讲交叉引用" % name)
        if re.search(r"[（(]19|20\d\d[）)]", t) and not any(m in t for m in MARKERS):
            warn.append("%s：含大量年份却无待核实标记，需确认是否已全部核验" % name)
    if warn:
        print("\n危险信号：")
        for w in warn:
            print("  ! " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
