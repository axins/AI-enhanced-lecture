#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全课程讲稿进度报告：字数、链接、类型分布、来源等级、三子块覆盖、待核实残留。

v3 变更：
- 每个文件只读一次、只扫描一次（旧版为统计与告警两轮读盘）
- 新增来源等级 T1—T4 分布列与「T3 占比过高」告警
- 新增 --json / --version

用法：
    python progress_report.py --dir .
    python progress_report.py --dir . --glob "*讲稿与教案.md"
    python progress_report.py --dir . --json progress.json
"""
import argparse
import glob
import io
import json
import os
import re
import sys

VERSION = "3.1"
LINK_TYPES = ["数据库DOI", "开放获取", "官方一手", "媒体报道", "判例数据"]
TIERS = ["T1", "T2", "T3", "T4"]
BLOCKS = ["【历史脉络】", "【逻辑关联】", "【参考链接】"]
MARKERS = ["需核实", "待核实", "待查", "存疑", "未核实"]
URL_RE = re.compile(r"https?://")
REF_RE = re.compile(r"回接\s*第?\s*\d+\s*讲|回接\s*L\d+")


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main():
    _utf8()
    ap = argparse.ArgumentParser(description="讲稿进度报告")
    ap.add_argument("--dir", default=".", help="课程目录")
    ap.add_argument("--glob", default="*.md", help="文件匹配模式")
    ap.add_argument("--json", default="", help="机器可读输出路径")
    ap.add_argument("--version", action="version", version="progress_report.py " + VERSION)
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
    if not files:
        print("未匹配到任何文件：%s" % os.path.join(a.dir, a.glob))
        return 2

    cols = ["字数", "链接", "DOI", "开放", "官方", "媒体", "判例", "T1", "T2", "T3", "待核"]
    hdr = ("%-22s" % "文件") + "".join("%7s" % h for h in cols)
    print(hdr)
    print("-" * len(hdr))

    tot = dict((t, 0) for t in LINK_TYPES)
    t_tier = dict((t, 0) for t in TIERS)
    t_blocks = dict((b, 0) for b in BLOCKS)
    t_char = t_link = t_ver = 0
    rows, warn = [], []

    for f in files:
        t = io.open(f, encoding="utf-8").read()
        name = os.path.basename(f)
        n_link = len(URL_RE.findall(t))
        cs = [t.count("[%s]" % k) for k in LINK_TYPES]
        ts = [t.count("[%s]" % k) for k in TIERS]
        ver = sum(t.count(m) for m in MARKERS)
        bs = [t.count(b) for b in BLOCKS]

        print(("%-22s" % name[:22]) + ("%7d" % len(t)) + ("%7d" % n_link) +
              "".join("%7d" % c for c in cs) +
              "%7d" % ts[0] + "%7d" % ts[1] + "%7d" % ts[2] + ("%7d" % ver))

        for k, c in zip(LINK_TYPES, cs):
            tot[k] += c
        for k, c in zip(TIERS, ts):
            t_tier[k] += c
        for b, c in zip(BLOCKS, bs):
            t_blocks[b] += c
        t_char += len(t)
        t_link += n_link
        t_ver += ver
        rows.append({"file": name, "chars": len(t), "links": n_link,
                     "by_type": dict(zip(LINK_TYPES, cs)),
                     "by_tier": dict(zip(TIERS, ts)),
                     "markers": ver, "blocks": dict(zip(BLOCKS, bs))})

        if t.count("http") > 5 and not any(t.count("[%s]" % k) for k in LINK_TYPES):
            warn.append("%s：链接多但无类型标签，可能是堆砌" % name)
        if n_link == 0 and len(t) > 20000:
            warn.append("%s：字数可观但无外部链接" % name)
        if n_link and sum(ts) == 0:
            warn.append("%s：链接未标来源等级，无法判断可信度" % name)
        total_t = sum(ts) or 0
        if total_t >= 10 and ts[2] / float(total_t) > 0.5:
            warn.append("%s：T3（整理稿/百科）占 %.0f%%，宜补 T1/T2 原始来源"
                        % (name, 100.0 * ts[2] / total_t))
        if not REF_RE.search(t):
            warn.append("%s：无跨讲交叉引用" % name)
        if re.search(r"[（(]19\d\d[）)]", t) and not any(m in t for m in MARKERS):
            warn.append("%s：含大量年份却无待核实标记，需确认是否已全部核验" % name)

    print("-" * len(hdr))
    print(("%-22s" % "合计") + ("%7d" % t_char) + ("%7d" % t_link) +
          "".join("%7d" % tot[k] for k in LINK_TYPES) +
          "%7d" % t_tier["T1"] + "%7d" % t_tier["T2"] + "%7d" % t_tier["T3"] +
          ("%7d" % t_ver))
    print("\n三子块合计：" + "　".join("%s %d" % (b, t_blocks[b]) for b in BLOCKS))
    print("来源等级合计：" + "　".join("%s %d" % (k, t_tier[k]) for k in TIERS))

    if warn:
        print("\n危险信号：")
        for w in warn:
            print("  ! " + w)

    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(json.dumps({
            "files": rows,
            "total": {"chars": t_char, "links": t_link, "markers": t_ver,
                      "by_type": tot, "by_tier": t_tier, "blocks": t_blocks},
            "warnings": warn,
        }, ensure_ascii=False, indent=2))
        print("\nJSON 已写入 %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
