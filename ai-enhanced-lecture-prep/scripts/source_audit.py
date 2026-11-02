#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""来源分级审计：检查链接是否标了类型与等级、等级是否与域名匹配、交付物是否带待核清单。

只做机械判定，不判断内容对错。三条规则：

1. 含链接的行必须同时有 [类型]（五选一）与 [等级]（T1—T4）。
2. 等级必须与域名相符：政府/法院/检察院/统计部门域名不得标 T3；
   百科与问答类域名不得标 T1/T2。
3. 交付物必须含「待核清单」章节。

用法：
    python source_audit.py --dir .
    python source_audit.py --dir . --glob "*讲稿*.md"
    python source_audit.py --dir . --strict --json audit.json
"""
import argparse
import glob
import io
import json
import os
import re
import sys
import urllib.parse

import _deck

VERSION = "3.1"
LINK_TYPES = ["数据库DOI", "开放获取", "官方一手", "媒体报道", "判例数据"]
TIERS = ["T1", "T2", "T3", "T4"]

URL_RE = re.compile(r"https?://[^\s\)\]（】\"'<>｜|]+")
TIER_RE = re.compile(r"\[(T[1-4])\]")
TYPE_RE = re.compile(r"\[(%s)\]" % "|".join(LINK_TYPES))

OFFICIAL_HOSTS = ("gov.cn", "court.gov.cn", "spp.gov.cn", "npc.gov.cn",
                  "stats.gov.cn", "moe.gov.cn", "moj.gov.cn", "chinacourt.org")
WEAK_HOSTS = ("baike.baidu.com", "baike.sogou.com", "baike.com", "wikipedia.org",
              "wikiwand.com", "zhidao.baidu.com", "zhihu.com", "douban.com",
              "360baike", "sogou.com", "so.com", "wenku.baidu.com")


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def host_of(url):
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""


def audit_text(text):
    problems, stats = [], {"links": 0, "untagged": 0, "untiered": 0,
                           "tier_mismatch": 0, "no_todo_list": False}
    for lineno, line in enumerate(text.splitlines(), 1):
        urls = URL_RE.findall(line)
        if not urls:
            continue
        stats["links"] += len(urls)
        has_type = bool(TYPE_RE.search(line))
        tiers = TIER_RE.findall(line)
        if not has_type:
            stats["untagged"] += 1
            problems.append("第 %d 行：链接未标类型（五选一：%s）"
                            % (lineno, "/".join(LINK_TYPES)))
        if not tiers:
            stats["untiered"] += 1
            problems.append("第 %d 行：链接未标来源等级（T1—T4）" % lineno)
            continue
        tier = tiers[0]
        for u in urls:
            h = host_of(u)
            if tier in ("T1", "T2") and any(w in h for w in WEAK_HOSTS):
                stats["tier_mismatch"] += 1
                problems.append("第 %d 行：%s 标为 %s，但域名属整理稿/百科类，宜降为 T3"
                                % (lineno, h or u, tier))
            elif tier == "T3" and any(o in h for o in OFFICIAL_HOSTS):
                stats["tier_mismatch"] += 1
                problems.append("第 %d 行：%s 为官方域名却标 T3，宜升为 T1" % (lineno, h))

    if "待核清单" not in text and "核查清单" not in text:
        stats["no_todo_list"] = True
        problems.append("缺少「待核清单」章节（交付前须列出未取到的原始文本与结论）")
    return problems, stats


def main():
    _utf8()
    ap = argparse.ArgumentParser(description="来源分级审计")
    ap.add_argument("--dir", default=".", help="扫描目录")
    ap.add_argument("--glob", default="*.md", help="文件匹配模式")
    ap.add_argument("--strict", action="store_true",
                    help="严格模式：任何未标注链接都算失败（默认仍会列出但退出码 0）")
    ap.add_argument("--json", default="", help="机器可读报告输出路径")
    ap.add_argument("--version", action="version", version="source_audit.py " + VERSION)
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
    if not files:
        print("未匹配到任何文件：%s" % os.path.join(a.dir, a.glob))
        return 2

    report, bad = {}, 0
    for f in files:
        raw = io.open(f, encoding="utf-8").read()
        problems, stats = audit_text(_deck.strip_page_content(raw))
        name = os.path.basename(f)
        report[name] = {"stats": stats, "problems": problems}
        flag = "!" if problems else "."
        print("%s %-42s 链接 %3d　缺类型 %2d　缺等级 %2d　等级不符 %2d"
              % (flag, name, stats["links"], stats["untagged"],
                 stats["untiered"], stats["tier_mismatch"]))
        if problems:
            bad += 1
            for p in problems[:8]:
                print("    - " + p)
            if len(problems) > 8:
                print("    - ……其余 %d 条见 JSON 明细" % (len(problems) - 8))

    print("\n扫描 %d 个文件，%d 个存在问题。" % (len(files), bad))
    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(
            json.dumps(report, ensure_ascii=False, indent=2))
        print("JSON 已写入 %s" % a.json)
    if a.strict and bad:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
