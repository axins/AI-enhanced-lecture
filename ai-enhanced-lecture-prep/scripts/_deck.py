#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""课件解析的共享层：格式兜底、单次解析、跨进程缓存。

设计要点
--------
1. 只解析一次。一次备课会多次用到页序信息（导出索引、生成骨架、质检比对）。
   旧版每个脚本各解析一遍，100 页以上的课件重复付出十几秒。
2. 缓存以「绝对路径 + 文件大小 + mtime」为键，课件一改即失效，不会读到旧数据。
3. .ppt / .doc 等旧二进制格式无法解析，明确报错并给出另存指令，
   而不是静默返回 0 页让后续步骤在空基线上跑。
"""
import hashlib
import json
import os
import re
import sys
import tempfile

CACHE_VERSION = 3
OLE_SUFFIXES = (".ppt", ".doc", ".pps", ".xls")
CACHE_DIR = os.path.join(tempfile.gettempdir(), "ai-lecture-prep-cache")


class DeckError(Exception):
    """课件无法读取：格式不支持、文件缺失、依赖缺失。"""


def _cache_dir():
    d = os.environ.get("AI_LECTURE_CACHE_DIR") or CACHE_DIR
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        return None
    return d


def _key(path):
    st = os.stat(path)
    raw = "%s|%d|%d|%d" % (os.path.abspath(path), st.st_size,
                           int(st.st_mtime), CACHE_VERSION)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _shape_text(sh):
    """抽取形状内文字：文本框、表格单元格、组合形状。"""
    out = []
    try:
        if sh.has_text_frame:
            t = sh.text_frame.text.strip()
            if t:
                out.append(t)
    except Exception:
        pass
    try:
        if getattr(sh, "has_table", False):
            for row in sh.table.rows:
                cells = [c.text.strip() for c in row.cells]
                if any(cells):
                    out.append(" | ".join(cells))
    except Exception:
        pass
    try:
        if sh.shape_type == 6:  # MSO_SHAPE_TYPE.GROUP
            for sub in sh.shapes:
                sub_text = _shape_text(sub)
                if sub_text:
                    out.append(sub_text)
    except Exception:
        pass
    return "\n".join(out)


def _parse(path):
    try:
        from pptx import Presentation
    except ImportError:
        raise DeckError("缺少依赖 python-pptx，请先安装：pip install python-pptx")

    prs = Presentation(path)
    pages = []
    for i, s in enumerate(prs.slides, 1):
        try:
            layout = s.slide_layout.name
        except Exception:
            layout = "?"
        parts = [_shape_text(sh) for sh in s.shapes]
        text = "\n".join(p for p in parts if p).strip()
        notes = ""
        try:
            if s.has_notes_slide:
                notes = s.notes_slide.notes_text_frame.text.strip()
        except Exception:
            notes = ""
        pages.append({
            "n": i,
            "layout": layout,
            "text": text,
            "notes": notes,
            "blank": not text,
            "first": " ".join(text.split())[:60] if text else "",
        })
    return pages


def load_deck(path, use_cache=True):
    """返回 {"pages": [...], "source": 路径, "cached": bool}。"""
    if not os.path.exists(path):
        raise DeckError("找不到课件文件：%s" % path)
    low = path.lower()
    if low.endswith(OLE_SUFFIXES):
        ext = os.path.splitext(low)[1]
        target = {".ppt": ".pptx", ".pps": ".pptx",
                  ".doc": ".docx", ".xls": ".xlsx"}.get(ext, "新格式")
        raise DeckError(
            "不支持的旧二进制格式：%s\n"
            "  .ppt/.doc 无法解析，请先用 PowerPoint/Word 另存为 %s 后重试。"
            % (os.path.basename(path), target))
    if not low.endswith((".pptx", ".pptm")):
        raise DeckError("不支持的课件格式：%s（仅支持 .pptx/.pptm）" % path)

    cdir = _cache_dir() if use_cache else None
    cpath = os.path.join(cdir, "deck-%s.json" % _key(path)) if cdir else None

    if cpath and os.path.exists(cpath):
        try:
            with open(cpath, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") == CACHE_VERSION:
                return {"pages": data["pages"], "source": path, "cached": True}
        except Exception:
            pass

    pages = _parse(path)
    if cpath:
        try:
            with open(cpath, "w", encoding="utf-8") as f:
                json.dump({"version": CACHE_VERSION, "pages": pages},
                          f, ensure_ascii=False)
        except Exception:
            pass
    return {"pages": pages, "source": path, "cached": False}


def deck_pages(path, use_cache=True):
    return len(load_deck(path, use_cache)["pages"])


BLOCK_HEAD = re.compile(r"^【([^】]+)】")


def strip_page_content(text):
    """去掉【页面内容】块（课件原文照抄，可能含网址、条号），
    只保留教师自己写的部分，供来源审计与链接检查使用。"""
    keep, skip = [], False
    for line in text.splitlines():
        m = BLOCK_HEAD.match(line.strip())
        if m:
            skip = (m.group(1) == "页面内容")
        if not skip:
            keep.append(line)
    return "\n".join(keep)


def utf8_stdout():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def fail(msg, code=2):
    """统一的错误出口：格式错误返回 2，便于批处理判断。"""
    print("[错误] " + msg)
    return code
