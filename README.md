# AI-enhanced-lecture

如何用 AI agent 高效备课：扩充课程材料、重做 ppt、核查事实、建设参考资料库，并设计 AI 增强的课堂与作业。

本仓库提供一个可直接使用的 CodeBuddy / Claude Skill：**`ai-enhanced-lecture-prep`**。

它沉淀了一套把一门大学社科课程从「几十页课件」扩展为「可讲授、可核查、可复用」的完整讲义的工作流，重点解决的是 **AI 在备课中到底该怎么用** 这个问题。

---

## 核心主张

> 在备课中，AI 的第一价值不是「帮你写」，而是「帮你发现错误」。

讲稿一旦进入课堂，错误的代价远高于论文——它会被几十名学生同时接收，且难以撤回。因此本 skill 把 AI 定位为**审计者**，其次才是检索者、结构化助手与对抗性陪练。

四个杠杆（详见 `ai-enhanced-lecture-prep/references/ai-for-prep.md`）：

| 杠杆 | AI 的角色 | 典型动作 |
|---|---|---|
| 一 | **审计者** | 时效审计、一致性审计、重复审计、盲点审计 |
| 二 | 检索者 | 补全文献出处、定位官方一手来源、找中英文媒体 |
| 三 | 结构化助手 | 把密集页面转成表格/板书/连续谱；为讨论题搭脚手架 |
| 四 | 对抗性陪练 | 扮演挑剔学生挑刺；生成反事实提问；预判误解点 |

配套方法：**三回答对照法**——学生先独立作答，再由 AI 作答，逐项对照差异，最后对 AI 输出做反向核查。目的不是让 AI 给标准答案，而是让学生看见自己的思考过程，并学会审计机器的回答。

---

## 安装

把 `ai-enhanced-lecture-prep/` 整个目录复制到 skill 目录：

```bash
# 用户级（所有项目可用）
~/.codebuddy/skills/ai-enhanced-lecture-prep/

# 或项目级（随仓库共享）
<项目>/.codebuddy/skills/ai-enhanced-lecture-prep/
```

---

## 目录结构

```
ai-enhanced-lecture-prep/
├── SKILL.md                          # 入口：原则、体例、工作流总览、脚本用法
├── references/
│   ├── workflow-phases.md            # 八阶段详细流程与每阶段交付物
│   ├── ai-for-prep.md                # 教师侧：AI 增强备课的四个杠杆（重点）
│   ├── ai-pedagogy.md                # 课堂侧：教学活动、作业规范与评分标准
│   ├── qa-rubric.md                  # 质检清单、验收门槛、10 种失败模式
│   └── prompt-library.md             # 备课与核查用提示词库
├── scripts/
│   ├── deck_index.py                 # 导出课件页序索引与指定页全文
│   ├── scaffold_lecture.py           # 按页序生成讲稿骨架
│   ├── qa_lecture.py                 # 覆盖度/重复/顺序/维度计数校验
│   ├── extract_todo.py               # 抽取待核实条目，生成核查清单
│   ├── check_links.py                # 批量校验参考链接存活性
│   └── progress_report.py            # 全课程进度报告与危险信号
└── assets/
    ├── lecture-notes-template.md     # 讲稿文件模板
    ├── reference-repo-template.md    # 参考资料总库模板（五分类）
    └── verify-list-template.md       # 待核实核查清单模板
```

---

## 八阶段工作流

| 阶段 | 名称 | 交付物 |
|---|---|---|
| P0 | 盘点与基线 | `page_index.md`（页序 + 页数指纹） |
| P1 | 骨架生成 | 讲稿骨架（每页四块） |
| P2 | 逐页扩展 | 按六类维度填充 + 三子块 |
| P3 | 质检 | 覆盖度/重复/顺序/维度校验报告 |
| P4 | 事实核查 | 核查清单（清零） |
| P5 | 资料总库 | 五分类参考资料库 |
| P6 | 交叉一致性 | 一致性报告（查冲突、查重复、统一术语） |
| P7 | 教学交付 | 讨论题、实证题目库、AI 活动、评分标准 |

关键纪律：**核查优先于扩展**（错误基础上的扩展会大量返工）、**逐页推进不批量**（一次性生成整册必然塌方）、**无法确认即标记**（标记是资产，不是瑕疵）。

---

## 快速开始

```bash
# 1. 盘点课件
python scripts/deck_index.py 课件.pptx --out page_index.md

# 2. 生成讲稿骨架
python scripts/scaffold_lecture.py 课件.pptx --out 讲稿.md

# 3. （逐页扩展后）质检
python scripts/qa_lecture.py 讲稿.md --deck 课件.pptx

# 4. 抽取待核实条目并逐条核查
python scripts/extract_todo.py --dir . --out verify_list.md

# 5. 校验参考链接
python scripts/check_links.py --dir .

# 6. 进度报告
python scripts/progress_report.py --dir .
```

依赖：`python-pptx`（P0/P1/P3）。未安装时脚本会给出提示而非崩溃。

---

## 讲稿体例

每页四块：

```markdown
## 第 N 页　<页面标题>

【页面内容】……（课件原文与备注）

【讲稿要点】……（一句话判断：本页最该讲的一处）

【需补充】
- ◤理论◢  ◤人物◢  ◤案例◢  ◤文献◢  ◤实践◢  ◤互动◢
```

核心条目另加三子块：`【历史脉络】`、`【逻辑关联】`（写明回接哪一讲哪一页）、`【参考链接】`（五类标签 + 访问日期）。

---

## 本 skill 与学科无关

文中所有 `<占位>` 需替换为具体课程信息。六类标注维度可用 `scaffold_lecture.py --dimensions` 定制。适用于任何社科或人文学科课程。

## 许可

MIT
