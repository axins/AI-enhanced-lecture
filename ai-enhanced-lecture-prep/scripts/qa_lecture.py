#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""讲稿质检：页序覆盖、重复、顺序、维度计数、空白页、标记词、交叉引用、链接、来源等级。

v3 变更：
- 单遍扫描（页级切片一次算出），避免旧版重复整篇正则
- 页数比对改走缓存，不再为「数一下有几页」重新解析整个课件
- 新增来源等级（T1—T4）统计与「待核清单」章节检查
- 新增 --strict（来源等级缺失即判失败）、--json（供批处理消费）、--version
- 退出码统一：0 通过 / 1 质检未通过 / 2 环境或参数错误

用法：
    python qa_lecture.py <讲稿.md>
    python qa_lecture.py <讲稿.md> --expect 52
    python qa_lecture.py <讲稿.md> --deck <deck.pptx>
    python qa_lecture.py <讲稿.md> --strict --json report.json
"""
import argparse
import io
import json
import os
import re
import sys

import _deck

VERSION = "3.1"
DEFAULT_DIMENSIONS = ["理论", "人物", "案例", "文献", "实践", "互动"]
DEFAULT_MARKERS = ["需核实", "待核实", "待查", "存疑", "未核实"]
LINK_TYPES = ["数据库DOI", "开放获取", "官方一手", "媒体报道", "判例数据"]
TIERS = ["T1", "T2", "T3", "T4"]
BLOCKS = ["【历史脉络】", "【逻辑关联】", "【参考链接】"]

PAGE_RE = re.compile(r"^## 第 (\d+) 页(.*)$", re.M)
REF_RE = re.compile(r"回接\s*第?\s*\d+\s*讲|回接\s*L\d+")
URL_RE = re.compile(r"https?://")


def count_pages(text):
    """返回 [(页号, 该页起始偏移, 标题行尾偏移)]，用于后续切片。"""
    return [(int(m.group(1)), m.start(), m.end()) for m in PAGE_RE.finditer(text)]


def main():
    _deck.utf8_stdout()
    ap = argparse.ArgumentParser(description="讲稿质检")
    ap.add_argument("notes", help="讲稿 .md 路径")
    ap.add_argument("--expect", type=int, default=0, help="应有页数")
    ap.add_argument("--deck", default="", help="课件 .pptx，用于比对页数")
    ap.add_argument("--dimensions", default="", help="标注维度，逗号分隔")
    ap.add_argument("--markers", default="", help="待核实标记词，逗号分隔")
    ap.add_argument("--min-refs", type=int, default=3, help="最少交叉引用数（默认 3）")
    ap.add_argument("--partial", action="store_true",
                    help="只校验已生成的部分页（分批推进时用，跳过缺页与页数不符）")
    ap.add_argument("--strict", action="store_true",
                    help="严格模式：链接必须带 T1—T4 来源等级，且必须含「待核清单」章节")
    ap.add_argument("--json", default="", help="机器可读报告输出路径")
    ap.add_argument("--no-cache", action="store_true", help="不读写课件解析缓存")
    ap.add_argument("--version", action="version", version="qa_lecture.py " + VERSION)
    a = ap.parse_args()

    dims = [d.strip() for d in a.dimensions.split(",") if d.strip()] or DEFAULT_DIMENSIONS
    markers = [m.strip() for m in a.markers.split(",") if m.strip()] or DEFAULT_MARKERS

    if not os.path.exists(a.notes):
        return _deck.fail("找不到讲稿文件：%s" % a.notes)
    text = io.open(a.notes, encoding="utf-8").read()

    heads = count_pages(text)
    pages = [h[0] for h in heads]

    expect = a.expect
    if not expect and a.deck:
        try:
            n = _deck.deck_pages(a.deck, use_cache=not a.no_cache)
            if n:
                expect = n
        except _deck.DeckError as e:
            return _deck.fail(str(e))
    if not expect:
        expect = max(pages) if pages else 0
    if a.partial:
        expect = max(pages) if pages else 0

    problems = []
    missing = sorted(set(range(1, expect + 1)) - set(pages))
    seen, dup = set(), []
    for p in pages:
        if p in seen and p not in dup:
            dup.append(p)
        seen.add(p)
    if missing:
        head = missing[:20]
        problems.append("缺页 %d 页：%s%s"
                        % (len(missing), head, "……" if len(missing) > 20 else ""))
    if dup:
        problems.append("重复页：%s" % sorted(dup))
    if pages != sorted(pages):
        problems.append("页号未递增：%s" % pages[:12])
    if expect and len(pages) != expect and not a.partial:
        problems.append("页数不符：%d（应为 %d）" % (len(pages), expect))

    # 空白页是否显式标注（按页切片，避免全文回溯）
    for idx, (num, start, head_end) in enumerate(heads):
        title = text[head_end:head_end + 60]
        if "空白页" in title or "无文字" in title:
            seg_end = heads[idx + 1][1] if idx + 1 < len(heads) else len(text)
            seg = text[start:seg_end]
            if "需补充" not in seg and "◤" not in seg:
                problems.append("第 %d 页（空白页）未给出处理建议" % num)

    # 维度计数（一次遍历）
    counts = dict((d, 0) for d in dims)
    dim_re = re.compile("◤(%s)◢" % "|".join(re.escape(d) for d in [d for d in dims]))
    for m in dim_re.finditer(text):
        if m.group(1) in counts:
            counts[m.group(1)] += 1
    for d in dims:
        if counts[d] == 0:
            problems.append("维度缺失：◤%s◢" % d)
    total_dim = sum(counts.values()) or 1
    for d in dims:
        if counts[d] / total_dim > 0.6:
            problems.append("维度失衡：◤%s◢ 占比 %.0f%%" % (d, 100.0 * counts[d] / total_dim))

    # 标记词
    marks = sum(text.count(m) for m in markers)

    # 交叉引用
    refs = len(REF_RE.findall(text))
    if refs < a.min_refs:
        problems.append("交叉引用不足：%d 条（建议 ≥%d）" % (refs, a.min_refs))

    # 链接与来源等级：只看教师撰写部分，不看【页面内容】里照抄的课件原文
    own = _deck.strip_page_content(text)
    urls = len(URL_RE.findall(own))
    typed = dict((t, own.count("[%s]" % t)) for t in LINK_TYPES)
    tiers = dict((t, own.count("[%s]" % t)) for t in TIERS)
    blocks = dict((b, text.count(b)) for b in BLOCKS)

    # 逐行判定：同时含 URL 的行是否带类型标签
    line_tag = re.compile(r"\[(?:%s)\]" % "|".join(LINK_TYPES))
    untyped = 0
    for line in own.splitlines():
        if URL_RE.search(line) and not line_tag.search(line):
            untyped += 1
    untiered = bool(urls) and sum(tiers.values()) == 0
    has_todo = "待核清单" in text
    if untyped:
        problems.append("链接未标类型：%d 行（共 %d 条链接）" % (untyped, urls))
    if a.strict:
        if untiered:
            problems.append("链接未标来源等级 T1—T4")
        if not has_todo:
            problems.append("缺少「待核清单」章节")

    print("文件：%s" % os.path.basename(a.notes))
    print("字数：%d　页：%d（应 %d）　链接：%d　待核清单：%s"
          % (len(text), len(pages), expect, urls, "有" if has_todo else "无"))
    print("维度：" + "　".join("◤%s◢ %d" % (d, counts[d]) for d in dims))
    print("链接类型：" + "　".join("%s %d" % (t, typed[t]) for t in LINK_TYPES))
    print("来源等级：" + "　".join("%s %d" % (t, tiers[t]) for t in TIERS))
    print("三子块：" + "　".join("%s %d" % (b, blocks[b]) for b in BLOCKS))
    print("交叉引用：%d 条　待核实标记：%d 处" % (refs, marks))
    print()

    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(json.dumps({
            "file": a.notes, "chars": len(text), "pages": len(pages),
            "expect": expect, "problems": problems,
            "dimensions": counts, "link_types": typed, "tiers": tiers,
            "refs": refs, "markers": marks, "has_todo_list": has_todo,
            "passed": not problems,
        }, ensure_ascii=False, indent=2))
        print("JSON 已写入 %s" % a.json)

    if problems:
        print("===== 质检未通过（%d 项）=====" % len(problems))
        for p in problems:
            print("[问题] " + p)
        return 1
    print("===== 质检通过 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
