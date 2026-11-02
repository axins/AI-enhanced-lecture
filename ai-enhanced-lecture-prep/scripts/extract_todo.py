#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽取讲稿中的「待核实」条目，生成带页号定位的核查清单。

v3 变更：
- 页号定位改为「一次预扫描 + 二分查找」，不再对每个标记回溯全文（长文档收益明显）
- 输出改为带结论列的表格式清单，与交付规范中的「待核清单」同构
- 新增 --json / --version
- 检索不到的条目在清单里明确写出处理口径，避免核查时含糊过关

用法：
    python extract_todo.py --dir . --out verify_list.md
    python extract_todo.py --dir . --glob "*讲稿*.md"
    python extract_todo.py --dir . --markers 需核实,待核实,存疑
"""
import argparse
import bisect
import glob
import io
import json
import os
import re
import sys

VERSION = "3.0"
DEFAULT_MARKERS = ["需核实", "待核实", "待查", "存疑", "未核实", "出处待核实"]
PAGE_RE = re.compile(r"^## 第 (\d+) 页", re.M)


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def page_index(text):
    """返回 (起始偏移列表, 页号列表)，供 bisect 定位。"""
    starts, nums = [], []
    for m in PAGE_RE.finditer(text):
        starts.append(m.start())
        nums.append(int(m.group(1)))
    return starts, nums


def locate(starts, nums, pos):
    i = bisect.bisect_right(starts, pos) - 1
    return nums[i] if 0 <= i < len(nums) else "?"


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
    ap.add_argument("--json", default="", help="机器可读输出路径")
    ap.add_argument("--version", action="version", version="extract_todo.py " + VERSION)
    a = ap.parse_args()

    markers = [m.strip() for m in a.markers.split(",") if m.strip()] or DEFAULT_MARKERS
    files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
    if not files:
        print("未匹配到任何文件：%s" % os.path.join(a.dir, a.glob))
        return 2

    marker_re = re.compile("|".join(re.escape(x) for x in markers))
    buf = ["# 讲稿「待核实」条目核查清单\n",
           "> 由 `extract_todo.py` 自动生成。核查完成后须回写讲稿并删除标记。\n",
           "> 三种合法结论：①已核实（写明来源等级 T1—T4）／"
           "②未检索到权威来源，建议课堂上不引用／③待观察（注明观察时点）。\n"]
    total, per_file, payload = 0, [], []
    for f in files:
        text = io.open(f, encoding="utf-8").read()
        starts, nums = page_index(text)
        rows = []
        for m in marker_re.finditer(text):
            end = text.find("\n", m.start())
            if end == -1:
                end = len(text)
            rows.append((locate(starts, nums, m.start()),
                         expand_item(text, m.start(), end)))
        if not rows:
            continue
        name = os.path.basename(f)
        per_file.append((name, len(rows)))
        total += len(rows)
        payload.append({"file": name, "count": len(rows),
                        "items": [{"page": p, "text": t} for p, t in rows]})
        buf.append("\n## %s（%d 处）\n" % (name, len(rows)))
        last = None
        for page, item in rows:
            if page != last:
                buf.append("\n### 第 %s 页\n\n" % page)
                buf.append("| 待核内容 | 未取到的原始文本 | 结论 | 来源等级 |\n")
                buf.append("|---|---|---|---|\n")
                last = page
            buf.append("| %s |  |  |  |\n" % item[:220].replace("|", "/"))

    buf.insert(3, "\n合计 %d 处；分布：%s\n" % (
        total, "、".join("%s %d" % (n, c) for n, c in per_file)))
    io.open(a.out, "w", encoding="utf-8").write("".join(buf))
    print("已写入 %s，合计 %d 处" % (a.out, total))
    for n, c in per_file:
        print("  %-42s %d" % (n, c))
    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(
            json.dumps({"total": total, "files": payload}, ensure_ascii=False, indent=2))
        print("JSON 已写入 %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
