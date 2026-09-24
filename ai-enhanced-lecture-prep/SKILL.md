---
name: ai-enhanced-lecture-prep
description: 用 AI 系统性地完成一门社科课程的备课——从课件盘点、逐页讲稿扩展、事实核查、参考资料库建设，到交叉讲次一致性检查与 AI 增强课堂活动设计。This skill should be used when the user asks to prepare, expand, revise, or restructure lecture materials (pptx/pdf) for a university course; to build a lecture-notes document with per-page structure; to verify facts, names, citations, or legal/statistical data across a whole course and add reference links; to detect duplicated content or inconsistent requirements across lectures; or to design AI-enhanced classroom discussions and assessment rubrics. Discipline-agnostic — applicable to any social science or humanities course.
---

# AI 增强社科课程备课

## 何时使用

在以下情形使用本 skill：

- 需要把一套课件（`.pptx`/`.pdf`）扩展为可讲授的讲稿与教案
- 需要为课程材料补入历史脉络、理论关联与外部参考链接
- 需要核查课件中的人名、文献卷期、法条条号、统计数据、案例事实
- 需要检查同一门课程内各讲之间是否存在内容重复或要求冲突
- 需要设计 AI 增强的课堂讨论、作业规范与评分标准
- 需要按学期推进、分批交付、每批完成后即可上课使用

本 skill 与学科无关。文中所有 `<占位>`（如 `<课程名>`、`<学科>`、`<核心概念>`）须在具体任务中替换。

## 核心原则

1. **先盘点，再动笔。** 任何扩展都建立在可核对的页序基线上。未导出页序索引前不得开始写作。
2. **逐页推进，禁止批量。** 一次性生成整册必然出现缺页、重复与质量塌方。按页序推进，每批完成后校验。
3. **核查优先于扩展。** 先修正已知错误，再补充新内容。否则扩展会建立在错误之上，返工成本极高。
4. **不确定即标记。** 凡无法当场确认的人名拼写、卷期页码、条号、数据，一律写入标记词（默认 `需核实`）。标记是资产，不是瑕疵。
5. **AI 的首要角色是审计者，不是写作者。** 备课中 AI 的最大价值在于找出过时、错误、重复与遗漏；生成内容反而是次要功能。
6. **链接必须检索获得。** 禁止凭记忆编造 URL、DOI、卷期或条号。检索不到即写「未检索到权威来源，建议课堂上不引用」。
7. **显式交叉引用。** 每讲至少建立若干条指向其他讲次的引用（`回接 第 N 讲 第 x 页`），这是课程整体感的来源。

## 目录结构

```
ai-enhanced-lecture-prep/
├── SKILL.md
├── references/
│   ├── workflow-phases.md      # 八阶段详细流程与每阶段交付物
│   ├── ai-for-prep.md          # 教师侧：AI 增强备课的四个杠杆（重点）
│   ├── ai-pedagogy.md          # 课堂侧：AI 增强教学活动与作业规范
│   ├── qa-rubric.md            # 质检清单、验收门槛与失败模式
│   └── prompt-library.md       # 备课与核查用提示词库
├── scripts/
│   ├── deck_index.py           # 导出课件页序索引与指定页全文
│   ├── scaffold_lecture.py     # 按页序生成讲稿骨架
│   ├── qa_lecture.py           # 覆盖度/重复/顺序/维度计数校验
│   ├── extract_todo.py         # 抽取待核实条目，生成核查清单
│   ├── check_links.py          # 批量校验参考链接存活性
│   └── progress_report.py      # 生成全课程进度报告
└── assets/
    ├── lecture-notes-template.md    # 讲稿文件模板（含文件头体例与文件尾附录）
    ├── reference-repo-template.md   # 参考资料总库模板（五分类）
    └── verify-list-template.md      # 待核实核查清单模板
```

## 工作流总览

| 阶段 | 名称 | 主要动作 | 交付物 |
|---|---|---|---|
| P0 | 盘点与基线 | 导出页序、记录页数指纹、建立基线图 | `page_index.md` |
| P1 | 骨架生成 | 按页序生成讲稿骨架 | `<课程>-第N讲-讲稿与教案.md` |
| P2 | 逐页扩展 | 按维度补内容，核心条目补三子块 | 同上（填充后） |
| P3 | 质检 | 覆盖度、重复、顺序、维度均衡 | 校验报告 |
| P4 | 事实核查 | 逐条检索核实并回写 | 核查清单（清零） |
| P5 | 资料总库 | 按五类集中存放链接，随讲累积 | `<课程>参考资料总库.md` |
| P6 | 交叉一致性 | 查重复、查冲突、查术语统一 | 一致性报告 |
| P7 | 教学交付 | 讨论题、实证题目、AI 活动、评分标准 | 课堂可用材料 |

详细步骤见 `references/workflow-phases.md`。

## 讲稿体例（必须沿用）

每一页固定为以下结构：

```markdown
## 第 N 页　<页面标题>

【页面内容】……（课件该页原文，含备注）

【讲稿要点】……（1—3 句，指出本页最该讲的一句或一处）

【需补充】
- ◤理论◢ ……
- ◤人物◢ ……
- ◤案例◢ ……
- ◤文献◢ ……
- ◤实践◢ ……
- ◤互动◢ ……
```

六类标注维度可按需增删（用 `scaffold_lecture.py --dimensions` 定制）。含义：

| 维度 | 内容 |
|---|---|
| `◤理论◢` | 概念澄清、理论来源、与其他理论的对照 |
| `◤人物◢` | 学者生平、代表作、学派归属、易混人名辨析 |
| `◤案例◢` | 案例事实补全、裁判要点、可类比的其他案例 |
| `◤文献◢` | 完整出处：作者、篇名、期刊/出版社、卷期、页码、年份 |
| `◤实践◢` | 制度现状、时效更新、数据补充、本土情境 |
| `◤互动◢` | 课堂提问与讨论设计，附参考答案或引路要点 |

**核心条目的三个子块**：对全课程反复出现的核心理论、关键人物、重要研究、支撑数据、典型案例，在该页【需补充】后追加：

```markdown
【历史脉络】……（产生背景、演进阶段、当代发展）
【逻辑关联】……（与本课程其他讲次的关系，写明「回接 第 N 讲 第 x 页」）
【参考链接】
- [数据库DOI] <URL>（访问日期）
- [开放获取] <URL>（访问日期）
- [官方一手] <URL>（访问日期）
- [媒体报道] <URL>（访问日期）
- [判例数据] <URL>（访问日期）
```

链接分类标签固定为五个：`[数据库DOI]`、`[开放获取]`、`[官方一手]`、`[媒体报道]`、`[判例数据]`。脚本按此标签统计。

## AI 增强备课的四个杠杆

完整说明见 `references/ai-for-prep.md`。摘要：

| 杠杆 | AI 的角色 | 典型动作 | 价值 |
|---|---|---|---|
| 一 | **审计者** | 时效审计、一致性审计、重复审计、盲点审计 | **最高** |
| 二 | **检索者** | 补全文献出处、定位官方一手来源、找中英文媒体 | 高 |
| 三 | **结构化助手** | 把密集页面转成表格/板书/连续谱；为讨论题搭脚手架 | 中 |
| 四 | **对抗性陪练** | 扮演挑剔学生挑刺；生成反事实提问；预判误解点 | 中高 |

**红线**：AI 给出的条号、年份、人名、判例数据，未经独立检索确认一律不得写入讲稿。备课错误会直接进入课堂，代价高于论文错误。

**与课堂方法同构**：备课端同样适用「三回答对照法」——先独立写下自己的判断与不确定的地方，再让 AI 作答，逐项比对差异，最后对 AI 输出做反向核查。

## 脚本用法

所有脚本接受 `--dir <课程目录>`（默认当前目录），输出 UTF-8。

```bash
# P0 盘点：导出页序索引
python scripts/deck_index.py <deck.pptx> --out page_index.md

# P0 盘点：查看指定页全文与备注
python scripts/deck_index.py <deck.pptx> --pages 1,2,5

# P1 骨架：按页序生成讲稿骨架
python scripts/scaffold_lecture.py <deck.pptx> --out 讲稿.md

# P3 质检：覆盖度、重复、顺序、维度计数
python scripts/qa_lecture.py 讲稿.md --deck <deck.pptx>

# P4 核查：抽取待核实条目
python scripts/extract_todo.py --dir . --out verify_list.md

# P5 总库：校验链接存活性
python scripts/check_links.py --dir .

# P7 交付：全课程进度报告
python scripts/progress_report.py --dir .
```

依赖：`python-pptx`（P0/P1/P3）、`python-docx`（仅在处理大纲时）。未安装时脚本应给出明确提示而非崩溃。

## 质检门槛

每讲交付前必须全部通过（用 `qa_lecture.py` 自动校验，详见 `references/qa-rubric.md`）：

- 页序覆盖：无缺页、无重复、页号严格递增
- 维度计数：六类维度均出现，且不严重失衡
- 空白页：显式标注而非静默跳过
- 待核实标记：数量归零或逐条给出结论
- 交叉引用：每讲至少 3 条指向其他讲次
- 链接：全部标注类型标签与访问日期，且通过存活性校验

## 常见失败模式

见 `references/qa-rubric.md`。最常见且代价最高的六种：

1. 一次性生成整册 → 缺页、重复、后半部分质量断崖
2. 不标「需核实」→ 错误静默进入讲稿，课堂上被学生指出
3. 凭记忆写文献卷期与法条条号 → 学术可信度受损
4. 未做跨讲一致性检查 → 同一门课出现三处互相冲突的作业要求
5. 平行讲次内容重复却不分工 → 学生认为在浪费时间
6. 只补内容不加交叉引用 → 课程碎片化，期末无法复习

## 参考文件索引

| 文件 | 何时读取 |
|---|---|
| `references/workflow-phases.md` | 开始任一阶段前，确认该阶段的动作与交付物 |
| `references/ai-for-prep.md` | 需要设计 AI 参与的备课环节时（重点） |
| `references/ai-pedagogy.md` | 设计课堂讨论、作业规范与评分标准时 |
| `references/qa-rubric.md` | 每讲交付前做质检、或排查质量问题时 |
| `references/prompt-library.md` | 需要现成的备课、核查、审计提示词时 |
