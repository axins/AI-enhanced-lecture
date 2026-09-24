#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出课件(.pptx)的页序索引；可选导出指定页全文与备注。

用法：
    python deck_index.py <deck.pptx>                  # 页序索引（表格）
    python deck_index.py <deck.pptx> --pages 1,2,5    # 指定页全文 + 备注
    python deck_index.py <deck.pptx> --out index.md   # 写入文件
"""
import argparse
import io
import sys

DEFAULT = "（本页无文字）"


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def slide_text(slide):
    parts = []
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            parts.append(sh.text_frame.text.strip())
    return "\n".join(parts)


def cell(text, limit=40):
    t = " ".join(text.split())
    if not t:
        return DEFAULT
    return t[:limit].replace("|", "/")


def main():
    _utf8()
    ap = argparse.ArgumentParser(description="课件页序索引导出")
    ap.add_argument("deck", help="课件 .pptx 路径")
    ap.add_argument("--pages", default="", help="仅导出这些页的全文，如 1,2,5")
    ap.add_argument("--out", default="", help="输出文件（默认打印到标准输出）")
    a = ap.parse_args()

    try:
        from pptx import Presentation
    except ImportError:
        print("缺少依赖 python-pptx，请先安装：pip install python-pptx")
        return 2

    slides = list(Presentation(a.deck).slides)
    lines = []

    if a.pages:
        for i in [int(x) for x in a.pages.split(",") if x.strip()]:
            if not 1 <= i <= len(slides):
                lines.append("第 %d 页不存在（共 %d 页）" % (i, len(slides)))
                continue
            s = slides[i - 1]
            lines.append("===== 第 %d 页（版式：%s） =====" % (i, s.slide_layout.name))
            t = slide_text(s)
            lines.append(t if t.strip() else DEFAULT)
            if s.has_notes_slide:
                nt = s.notes_slide.notes_text_frame.text.strip()
                if nt:
                    lines.append("--- 备注 ---")
                    lines.append(nt)
            lines.append("")
    else:
        lines.append("总页数：%d" % len(slides))
        lines.append("")
        lines.append("| 页号 | 版式 | 首行文本 |")
        lines.append("|---|---|---|")
        for i, s in enumerate(slides, 1):
            lines.append("| %d | %s | %s |" % (i, s.slide_layout.name, cell(slide_text(s))))
        blank = [i for i, s in enumerate(slides, 1) if not slide_text(s).strip()]
        if blank:
            lines.append("")
            lines.append("无文字页（图片页/空白页）：%s" % ", ".join(map(str, blank)))

    out = "\n".join(lines)
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(out + "\n")
        print("已写入 %s" % a.out)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
