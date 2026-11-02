#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量校验 Markdown 中参考链接的存活性，输出失效/待确认清单。

v3 变更：
- 并发探测（默认 8 线程），串行的逐条等待改为并行，链接多的课程目录收益最大
- 结果缓存（默认 7 天 TTL），反复复检时只请求新增或过期的链接
- 相同 URL 在同一批里只探测一次（跨文件去重）
- 新增 --jobs / --cache-ttl / --strict / --version
- 有失效链接时退出码 1，便于接入批处理

用法：
    python check_links.py --dir .
    python check_links.py --dir . --glob "*L7*"
    python check_links.py --dir . --timeout 10 --jobs 12
    python check_links.py --dir . --json report.json
"""
import argparse
import glob
import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

VERSION = "3.0"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

URL_RE = re.compile(
    r"https?://[^\s\)\]（】\"'<>｜|\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]+")

BLOCKED_CODES = (401, 403, 405, 412, 429, 451)
SKIP_HOSTS = ("cnki.net", "jstor.org", "doi.org", "scholar.google",
              "westlaw", "lexisnexis", "sci-hub")
LINK_TYPES = ["数据库DOI", "开放获取", "官方一手", "媒体报道", "判例数据"]
NET_ERR = ("URLError", "TimeoutError", "socket.timeout", "SSLError",
           "ConnectionResetError", "RemoteDisconnected", "IncompleteRead")

CACHE_FILE = os.path.join(tempfile.gettempdir(), "ai-lecture-prep-cache",
                          "link-status.json")


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def load_cache(ttl):
    if ttl <= 0:
        return {}
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}
    now = time.time()
    return {u: v for u, v in raw.items() if now - v.get("ts", 0) < ttl}


def save_cache(cache):
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
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
            if code < 300:
                return "ok"
            if code < 400:
                # 未被自动跟随的重定向（登录墙、循环跳转）不算失效，交人工判断
                return "blocked:%s" % code
            return "dead:%s" % code
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
    ap.add_argument("--jobs", type=int, default=8, help="并发线程数（默认 8）")
    ap.add_argument("--cache-ttl", type=int, default=7 * 86400,
                    help="结果缓存有效期（秒，默认 7 天；0 表示禁用）")
    ap.add_argument("--json", default="", help="明细 JSON 输出路径")
    ap.add_argument("--strict", action="store_true", help="存在失效链接时返回退出码 1")
    ap.add_argument("--version", action="version", version="check_links.py " + VERSION)
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
    if not files:
        print("未匹配到任何文件：%s" % os.path.join(a.dir, a.glob))
        return 2

    t0 = time.time()
    texts = {}
    per_file_urls = {}
    all_urls = set()
    for f in files:
        t = io.open(f, encoding="utf-8").read()
        texts[f] = t
        us = sorted(set(URL_RE.findall(t)))
        per_file_urls[f] = us
        all_urls.update(us)

    cache = load_cache(a.cache_ttl)
    todo = [u for u in all_urls if u not in cache]
    status = {u: cache[u]["st"] for u in all_urls if u in cache}

    if todo:
        with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
            for u, st in zip(todo, ex.map(lambda x: probe(x, a.timeout), todo)):
                status[u] = st
        now = time.time()
        for u in todo:
            cache[u] = {"st": status[u], "ts": now}
        save_cache(cache)

    report, tot = {}, {"ok": 0, "dead": 0, "blocked": 0, "skip": 0}
    for f in files:
        urls = per_file_urls[f]
        dead, blocked, skip = [], [], []
        for u in urls:
            st = status[u]
            tot[st.split(":")[0]] += 1
            if st == "ok":
                continue
            if st == "skip":
                skip.append(u)
            elif st.startswith("blocked"):
                blocked.append((u, st))
            else:
                dead.append((u, st))
        name = os.path.basename(f)
        t = texts[f]
        report[name] = {
            "total": len(urls),
            "by_type": dict((k, t.count("[%s]" % k)) for k in LINK_TYPES),
            "by_tier": dict((k, t.count("[%s]" % k)) for k in ("T1", "T2", "T3", "T4")),
            "dead": dead, "blocked": blocked, "skipped": skip,
        }
        print("%-42s 链接 %3d　失效 %d　待确认 %d　跳过 %d"
              % (name, len(urls), len(dead), len(blocked), len(skip)))

    cost = time.time() - t0
    print("\n合计：可用 %d　失效 %d　待确认 %d　跳过 %d　（%d 条链接，本次实探 %d 条，%.1fs）"
          % (tot["ok"], tot["dead"], tot["blocked"], tot["skip"],
             len(all_urls), len(todo), cost))
    if tot["dead"]:
        print("\n失效链接需替换或删除：")
        for name, r in report.items():
            for u, st in r["dead"]:
                print("  [%s] %s  (%s)" % (name, u, st))
    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(
            json.dumps(report, ensure_ascii=False, indent=2))
        print("\n明细已写入 %s" % a.json)
    return 1 if (a.strict and tot["dead"]) else 0


if __name__ == "__main__":
    sys.exit(main())
