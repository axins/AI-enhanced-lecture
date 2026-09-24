#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按课件页序生成讲稿骨架(.md)：文件头体例 + 每页四块 + 文件尾两附录。

用法：
    python scaffold_lecture.py <deck.pptx> --out 讲稿.md
    python scaffold_lecture.py <deck.pptx> --out 讲稿.md --pages 1-20
    python scaffold_lecture.py <deck.pptx> --out 讲稿.md --dimensions 理论,人物,案例,文献,实践,互动
    python scaffold_lecture.py <deck.pptx> --out 讲稿.md --no-content   # 不填充页面原文
"""
import argparse
import io
import sys

DEFAULT_DIMENSIONS = ["理论", "人物", "案例", "文献", "实践", "互动"]
DIMENSION_DESC = {
    "理论": "概念澄清、理论来源、与其他理论的对照",
    "人物": "学者代表作、学派归属、易混人名辨析",
    "案例": "案例事实补全、处理要点、可类比的其他案例",
    "文献": "完整出处：作者、篇名、期刊/出版社、卷期、页码、年份",
    "实践": "制度现状、时效更新、数据补充、本土情境",
    "互动": "课堂提问与讨论设计，须附参考答案或引路要点",
}


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


def parse_pages(spec, total):
    if not spec:
        return list(range(1, total + 1))
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [i for i in out if 1 <= i <= total]


def main():
    _utf8()
    ap = argparse.ArgumentParser(description="讲稿骨架生成")
    ap.add_argument("deck", help="课件 .pptx 路径")
    ap.add_argument("--out", required=True, help="输出的 .md 路径")
    ap.add_argument("--pages", default="", help="仅生成这些页，如 1-20 或 1,2,5")
    ap.add_argument("--dimensions", default="", help="标注维度，逗号分隔（默认 %s）" % ",".join(DEFAULT_DIMENSIONS))
    ap.add_argument("--title", default="", help="讲次标题，用于文件头")
    ap.add_argument("--no-content", action="store_true", help="不填充【页面内容】")
    a = ap.parse_args()

    try:
        from pptx import Presentation
    except ImportError:
        print("缺少依赖 python-pptx，请先安装：pip install python-pptx")
        return 2

    dims = [d.strip() for d in a.dimensions.split(",") if d.strip()] or DEFAULT_DIMENSIONS
    slides = list(Presentation(a.deck).slides)
    pages = parse_pages(a.pages, len(slides))

    buf = []
    title = a.title or "第 N 讲"
    buf.append("# %s　讲稿与教案\n" % title)
    buf.append("> 由 `scaffold_lecture.py` 生成。课件共 %d 页，本骨架覆盖 %d 页。\n" % (len(slides), len(pages)))
    buf.append("## 体例说明\n")
    buf.append("- 每页四块：`【页面内容】`（课件原文与备注）→ `【讲稿要点】`（一句判断）→ `【需补充】`（按维度）→ 可选三子块。\n")
    buf.append("- 标注维度：\n")
    for d in dims:
        buf.append("  - `◤%s◢`　%s\n" % (d, DIMENSION_DESC.get(d, "")))
    buf.append("- 三子块（用于核心理论／关键人物／重要研究／支撑数据／典型案例）："
               "`【历史脉络】`、`【逻辑关联】`（写明「回接 第 N 讲 第 x 页」）、`【参考链接】`。\n")
    buf.append("- 参考链接五类标签：`[数据库DOI]`、`[开放获取]`、`[官方一手]`、`[媒体报道]`、`[判例数据]`，每条标注访问日期。\n")
    buf.append("- 无法确认的人名拼写、卷期、条号、数据，一律写标记词 `需核实`，不得猜测。\n")
    buf.append("\n---\n")

    for i in pages:
        s = slides[i - 1]
        txt = slide_text(s).strip()
        head = " ".join(txt.split())[:36] if txt else "（空白页）"
        buf.append("\n## 第 %d 页　%s\n" % (i, head))
        buf.append("\n【页面内容】")
        if a.no_content:
            buf.append("（待填）")
        else:
            buf.append(txt if txt else "无文字（原为图片页）。")
            if s.has_notes_slide:
                nt = s.notes_slide.notes_text_frame.text.strip()
                if nt:
                    buf.append("\n\n> 备注：%s" % nt.replace("\n", "\n> "))
        buf.append("\n\n【讲稿要点】（一句话判断：本页最该讲的一处）\n")
        buf.append("\n【需补充】\n")
        for d in dims:
            buf.append("- ◤%s◢ \n" % d)

    buf.append("\n---\n\n## 附：本讲最需要修改的若干处（按优先级）\n")
    buf.append("\n1. （待填）\n")
    buf.append("\n## 附：本讲可供学生做的实证研究题目\n")
    buf.append("\n1. （待填，每题标明：研究问题｜检验本讲哪一页的哪个命题｜方法与样本量｜数据来源）\n")

    io.open(a.out, "w", encoding="utf-8").write("".join(buf))
    print("已生成 %s（%d 页，维度 %d 类）" % (a.out, len(pages), len(dims)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
