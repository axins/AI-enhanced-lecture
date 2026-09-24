#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量校验 Markdown 中参考链接的存活性，输出失效/待确认清单。

用法：
    python check_links.py --dir .                  # 扫描目录下全部 .md
    python check_links.py --dir . --glob "*L7*"    # 只扫匹配的文件
    python check_links.py --dir . --timeout 10     # 自定义超时（默认 8 秒）
    python check_links.py --dir . --json report.json
"""
import argparse
import glob
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# 排除 CJK 与常见全角标点，避免把相邻中文连进 URL
URL_RE = re.compile(
    r"https?://[^\s\)\]（】\"'<>｜|\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]+")

# 反爬 / 网络类状态不算失效，归入「待人工确认」
BLOCKED_CODES = (401, 403, 405, 412, 429, 451)

# 已知可访问但常被反爬拦截的域名，跳过实际请求
SKIP_HOSTS = ("cnki.net", "jstor.org", "doi.org", "scholar.google",
              "westlaw", "lexisnexis", "sci-hub")

LINK_TYPES = ["数据库DOI", "开放获取", "官方一手", "媒体报道", "判例数据"]

NET_ERR = ("URLError", "TimeoutError", "socket.timeout", "SSLError",
           "ConnectionResetError", "RemoteDisconnected", "IncompleteRead")


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def probe(url, timeout):
    host = urllib.parse.urlparse(url).netloc.lower()
    if any(h in host for h in SKIP_HOSTS):
        return "skip"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for method in ("HEAD", "GET"):
        try:
            r = urllib.request.urlopen(req, timeout=timeout)
            code = r.getcode()
            r.close()
            return "ok" if code < 400 else "dead:%s" % code
        except urllib.error.HTTPError as e:
            if e.code in BLOCKED_CODES:
                return "blocked:%s" % e.code
            if method == "HEAD" and e.code in (405, 501):
                continue
            return "dead:%s" % e.code
        except Exception as e:
            name = type(e).__name__
            if method == "HEAD":
                continue
            return ("blocked:%s" % name) if name in NET_ERR else ("dead:%s" % name)
    return "blocked:unknown"


def main():
    _utf8()
    ap = argparse.ArgumentParser(description="参考链接存活性校验")
    ap.add_argument("--dir", default=".", help="课程目录")
    ap.add_argument("--glob", default="*.md", help="文件匹配模式")
    ap.add_argument("--timeout", type=int, default=8, help="单次请求超时秒数")
    ap.add_argument("--json", default="", help="明细 JSON 输出路径")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
    if not files:
        print("未匹配到任何文件：%s" % os.path.join(a.dir, a.glob))
        return 1

    report, tot = {}, {"ok": 0, "dead": 0, "blocked": 0, "skip": 0}
    for f in files:
        text = io.open(f, encoding="utf-8").read()
        urls = sorted(set(URL_RE.findall(text)))
        dead, blocked, skip = [], [], []
        for u in urls:
            st = probe(u, a.timeout)
            tot[st.split(":")[0]] += 1
            if st == "ok":
                continue
            (skip if st == "skip" else blocked if st.startswith("blocked") else dead).append(
                u if st == "skip" else (u, st))
            time.sleep(0.15)
        name = os.path.basename(f)
        report[name] = {
            "total": len(urls),
            "by_type": {t: len(re.findall(r"\[%s\]" % t, text)) for t in LINK_TYPES},
            "dead": dead, "blocked": blocked, "skipped": skip,
        }
        print("%-42s 链接 %3d　失效 %d　待确认 %d　跳过 %d"
              % (name, len(urls), len(dead), len(blocked), len(skip)))

    print("\n合计：可用 %d　失效 %d　待确认 %d　跳过 %d"
          % (tot["ok"], tot["dead"], tot["blocked"], tot["skip"]))
    if tot["dead"]:
        print("\n失效链接需替换或删除：")
        for name, r in report.items():
            for u, st in r["dead"]:
                print("  [%s] %s  (%s)" % (name, u, st))
    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(
            json.dumps(report, ensure_ascii=False, indent=2))
        print("\n明细已写入 %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
