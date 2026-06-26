# 📄 PDF Precision Skill

> 面向复杂 PDF 文档的高精度数据提取、结构化索引、证据问答与自动评测 Skill。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PDF](https://img.shields.io/badge/Task-PDF%20Extraction-orange)
![Skill](https://img.shields.io/badge/Type-Agent%20Skill-green)
![Evaluation](https://img.shields.io/badge/Evaluation-Supported-purple)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## ✨ 项目简介

本项目实现了一个面向复杂 PDF 的 **precision-first** 数据抽取与问答 Skill。

系统以真实复杂 PDF —— **美团 2025 年度报告繁体中文版** 作为主数据集，支持：

* 📌 PDF 预检
* 🔍 多引擎文本与表格抽取
* 🧱 结构化事实构建
* 📊 财务指标问答
* 🧮 派生计算
* 🧾 证据页码与原始行定位
* 🚫 无答案拒答
* ✅ 自动评测
* 🤖 不依赖 PI-Agent 的轻量 mini-agent 执行流程

本项目的核心不是“把 PDF 文本读出来”，而是形成一个完整闭环：

```text
PDF 预检
→ 多通道抽取
→ 结构化索引
→ 证据优先问答
→ 数值归一化
→ 拒答机制
→ 自动评测
```

---

## 🎯 任务目标

本项目对应任务为：

> pdf-precision-skill 构建与优化
> 实现复杂文档的高精度数据提取和分析，例如根据用户 query 精准返回 PDF 中的财务数据、表格数据，甚至支持跨文档复杂数据分析扩展。

任务要求包括：

* ✅ 完整记录构建流程、优化流程和评测流程；
* ✅ 自主构造测试集；
* ✅ 保证 Skill 精度可用；
* ✅ 交付 `skills` 目录打包和一份简要实操报告；
* ✅ Bonus：不依赖现有 PI-Agent 产品，实现 skills 的原始 Agent 执行逻辑。

---

## 🧠 核心能力

### 1. 📋 PDF 预检

对输入 PDF 进行质量和风险检查，包括：

* 页数；
* 元数据；
* 页面文本密度；
* 疑似扫描页；
* 页面旋转情况；
* 损坏风险；
* 复杂表格和抽取风险。

对应脚本：

```bash
scripts/preflight.py
```

---

### 2. 🧩 多引擎 PDF 抽取

系统不依赖单一 PDF 解析工具，而是采用多引擎组合抽取：

| 引擎                | 作用                                |
| ----------------- | --------------------------------- |
| PyMuPDF           | 抽取文本块、bbox 和页面结构                  |
| pdfplumber        | 抽取词级信息和基础表格                       |
| pdftotext -layout | 作为 CJK 字体乱码 fallback，保留阅读顺序和表格行结构 |
| line-table parser | 解析年报中“指标 + 多年数值”的表格行              |
| Camelot           | 可选表格解析工具，默认关闭                     |

对应脚本：

```bash
scripts/extract_pdf.py
```

---

### 3. 🧱 结构化索引构建

抽取结果会被构建成可检索索引，主要包括：

| 索引类型   | 内容     |
| ------ | ------ |
| blocks | 文本块    |
| tables | 表格或行表格 |
| facts  | 结构化事实  |
| pages  | 页面级文本  |

例如财务概要中的一行：

```text
收入 364,854,746 337,591,576 276,744,954 ...
```

会被转成结构化事实：

```json
{
  "metric": "收入",
  "year": "2025",
  "answer": "364,854,746",
  "unit": "人民幣千元",
  "page": 7,
  "source": "pdftotext-line-table"
}
```

对应脚本：

```bash
scripts/build_index.py
```

---

### 4. 🔎 证据优先问答

问答流程采用：

```text
fact-first → table-cell → text-block → abstain
```

也就是：

1. 优先从结构化 facts 中查找精确答案；
2. 如果 facts 无法命中，再尝试表格单元格；
3. 如果表格无法命中，再尝试文本块；
4. 如果没有可靠证据，则拒答。

回答结果包含：

* `answer`
* `normalized_answer`
* `unit`
* `confidence`
* `evidence_page`
* `metric`
* `source_line`
* `audit_trace`

对应脚本：

```bash
scripts/answer_query.py
```

---

### 5. ✅ 自动评测

系统支持使用自主构建的 gold QA 测试集进行评测。

评测指标包括：

| 指标                | 含义          |
| ----------------- | ----------- |
| exact_match       | 答案字符串是否完全一致 |
| numeric_accuracy  | 数值归一化后是否准确  |
| evidence_accuracy | 证据页码是否命中    |
| abstain_accuracy  | 无答案问题是否正确拒答 |

对应脚本：

```bash
scripts/evaluate.py
```

---

### 6. 🤖 Bonus：轻量 Agent 执行逻辑

项目额外实现了一个不依赖 PI-Agent 产品的轻量 Agent 执行链路：

```text
Planner
→ Preflight Tool
→ Extract Tool
→ Index Tool
→ Query Tool
→ Verifier
→ Final Answer
```

对应脚本：

```bash
scripts/mini_agent.py
```

说明：

> 当前 `mini_agent.py` 是一个工具编排型 Agent，采用确定性 planner 实现任务拆解和工具调用，不依赖本地 LLM。
> 该设计主要考虑财报 PDF 数值问答对精度和证据可追溯要求较高，因此核心答案由结构化 facts 和证据校验返回。

---

## 📁 项目目录结构

```text
skills/pdf_precision_skill/
├── SKILL.md
├── README.md
├── requirements.txt
├── configs/
│   └── default.yaml
├── scripts/
│   ├── preflight.py
│   ├── extract_pdf.py
│   ├── build_index.py
│   ├── answer_query.py
│   ├── evaluate.py
│   ├── make_eval_set.py
│   ├── make_meituan_eval_set.py
│   ├── mini_agent.py
│   └── normalize.py
├── tests/
│   └── eval_set/
│       ├── meituan_2025_annual_report_tc.pdf
│       ├── questions.jsonl
│       └── metadata.json
└── examples/
    └── meituan_run/
        ├── extracted.jsonl
        └── index.json
```

---

## 📚 数据集说明

本项目使用 **美团 2025 年度报告繁体中文版** 作为主测试数据源。

该 PDF 具有以下特点：

* 📄 共 345 页，适合测试长文档索引和定位能力；
* 🧾 包含封面、目录、公司资料、财务概要、管理层讨论、审计报告、财务报表和附注；
* 🌐 语言以繁体中文为主，夹杂英文公司名、地址、股票代码和会计术语；
* 📊 表格密集，包括财务概要、分部财务资料、综合收益表、综合财务状况表、综合现金流量表等；
* ⚠️ 存在真实 PDF 抽取难点，例如部分繁体中文字体映射会导致 PyMuPDF / pdfplumber 抽取乱码。

测试集位于：

```text
tests/eval_set/questions.jsonl
```

当前测试集包含 30 条 gold QA，覆盖：

| 类型      | 示例                  |
| ------- | ------------------- |
| 财务概要五年表 | 收入、毛利、总资产、总负债       |
| 分部财务资料  | 核心本地商业、新业务、总收入      |
| 正式财务报表  | 综合收益表、综合财务状况表、现金流量表 |
| 公司资料    | 股票代码、董事长兼 CEO、总部城市  |
| 派生计算    | 2025 年收入较 2024 年增加额 |
| 拒答样本    | 文档中不存在的 2026 年收入    |

示例 gold QA：

```json
{
  "id": "mt_001",
  "query": "財務概要中，2025年的收入是多少？",
  "answer": "364,854,746",
  "unit": "人民幣千元",
  "evidence_pages": [7],
  "type": "table_cell_numeric"
}
```

```json
{
  "id": "mt_021",
  "query": "2025年收入相比2024年增加了多少人民幣千元？",
  "answer": "27,263,170",
  "unit": "人民幣千元",
  "evidence_pages": [7],
  "type": "derived_numeric"
}
```

```json
{
  "id": "mt_030",
  "query": "文檔中能否找到2026年收入？",
  "answer": null,
  "evidence_pages": [],
  "type": "negative_abstain"
}
```

---

## ⚙️ 环境安装

### 方式一：使用 conda

```bash
conda create -n pdf_precision python=3.10 -y
conda activate pdf_precision
```

进入项目目录：

```bash
cd skills/pdf_precision_skill
```

安装 Python 依赖：

```bash
pip install -r requirements.txt
```

安装 `poppler`，用于支持 `pdftotext -layout`：

```bash
conda install -c conda-forge poppler -y
```

检查安装是否成功：

```bash
python --version
pdftotext -v
```

---

### 可选：安装 Camelot

Camelot 默认不是必须启用。若需要增强表格解析能力，可安装：

```bash
conda install -c conda-forge ghostscript opencv -y
pip install "camelot-py[cv]"
```

启用 Camelot：

```bash
export PDF_PRECISION_ENABLE_CAMELOT=1
```

Windows PowerShell：

```powershell
$env:PDF_PRECISION_ENABLE_CAMELOT="1"
```

---

## 🚀 快速开始

### 1. 创建 outputs 目录

```bash
mkdir -p outputs
```

Windows PowerShell：

```powershell
mkdir outputs
```

---

### 2. PDF 预检

```bash
python scripts/preflight.py \
  tests/eval_set/meituan_2025_annual_report_tc.pdf \
  --out outputs/preflight.json
```

输出：

```text
outputs/preflight.json
```

---

### 3. PDF 内容抽取

```bash
python scripts/extract_pdf.py \
  tests/eval_set/meituan_2025_annual_report_tc.pdf \
  --out outputs/extracted.jsonl
```

输出：

```text
outputs/extracted.jsonl
```

---

### 4. 构建索引

```bash
python scripts/build_index.py \
  outputs/extracted.jsonl \
  --out outputs/index.json
```

输出：

```text
outputs/index.json
```

---

### 5. 单条问答

```bash
python scripts/answer_query.py \
  --index outputs/index.json \
  --query "2025年美团收入是多少"
```

期望输出示例：

```text
answer: 364,854,746
unit: 人民幣千元
evidence_page: 7
metric: 收入
source: pdftotext-line-table
```

也可以测试：

```bash
python scripts/answer_query.py \
  --index outputs/index.json \
  --query "2025年美团毛利是多少"
```

```bash
python scripts/answer_query.py \
  --index outputs/index.json \
  --query "2024年美团总资产是多少"
```

```bash
python scripts/answer_query.py \
  --index outputs/index.json \
  --query "文檔中能否找到2026年收入？"
```

---

### 6. 批量预测

如果 `answer_query.py` 支持批量参数：

```bash
python scripts/answer_query.py \
  --index outputs/index.json \
  --dataset tests/eval_set/questions.jsonl \
  --out outputs/predictions.jsonl
```

---

### 7. 自动评测

```bash
python scripts/evaluate.py \
  --dataset tests/eval_set/questions.jsonl \
  --pred outputs/predictions.jsonl \
  --out outputs/eval_result.json
```

输出：

```text
outputs/eval_result.json
```

---

### 8. mini-agent 演示

```bash
python scripts/mini_agent.py \
  tests/eval_set/meituan_2025_annual_report_tc.pdf \
  "2025年美团收入是多少"
```

该命令会演示：

```text
Planner → Preflight Tool → Extract Tool → Index Tool → Query Tool → Verifier → Final Answer
```

---

## 🔁 重新生成美团测试集

如果需要从原始 PDF 重新生成测试集：

```bash
python scripts/make_meituan_eval_set.py \
  --source-pdf /path/to/20260424065602215412120050_tc.pdf \
  --out tests/eval_set
```

生成结果：

```text
tests/eval_set/
├── meituan_2025_annual_report_tc.pdf
├── questions.jsonl
└── metadata.json
```

---

## 🛠️ 优化记录

### 1. 繁体中文字体乱码

真实美团年报中，部分页面存在嵌入字体编码问题。单独使用 PyMuPDF 或 pdfplumber 时，可能出现繁体中文乱码。

优化方式：

* 引入 `pdftotext -layout` fallback；
* 当页面文本疑似乱码时，优先使用 layout 文本；
* 保留表格行结构，方便后续 line-table facts 抽取。

---

### 2. 大 PDF 表格解析慢

美团年报共 345 页，如果默认对全页启用 Camelot，解析成本较高，且在部分页面效果不稳定。

优化方式：

* 默认关闭 Camelot；
* 使用 `pdftotext-layout + line-table parser` 作为主表格抽取路径；
* 允许通过环境变量启用 Camelot 作为增强能力。

---

### 3. 正文数字容易误召回

年报正文中经常出现大量财务数字，如果直接从文本块中检索，容易将正文数字误认为表格答案。

优化方式：

* 优先使用结构化 facts；
* 对 metric 进行质量排序；
* 完全匹配优先，前缀匹配其次，关键词包含最低；
* 返回答案时必须带 evidence page 和 source line。

---

### 4. 无答案问题容易幻觉

针对文档中不存在的问题，例如“2026 年收入”，系统不能根据相似年份或上下文编造答案。

优化方式：

* 构造 negative abstain 测试样本；
* 当无可靠 evidence 时返回拒答；
* 在评测中加入 `abstain_accuracy`。

---

## 📊 Smoke Test

当前已完成完整链路 smoke test：

```text
PDF
→ extract_pdf.py
→ extracted.jsonl
→ build_index.py
→ index.json
→ answer_query.py
```

典型结果：

| Query         |      Answer | Evidence           |
| ------------- | ----------: | ------------------ |
| 2025年美团收入是多少  | 364,854,746 | page 7, metric=收入  |
| 2025年美团毛利是多少  | 111,008,626 | page 7, metric=毛利  |
| 2024年美团总资产是多少 | 324,354,917 | page 7, metric=總資產 |

完整评测结果可通过以下命令生成：

```bash
python scripts/evaluate.py \
  --dataset tests/eval_set/questions.jsonl \
  --pred outputs/predictions.jsonl \
  --out outputs/eval_result.json
```

---

## 🧭 设计原则

本项目采用 **precision-first** 设计。

对于财报类 PDF 问答，直接让大模型生成数字容易出现：

* 年份混淆；
* 指标混淆；
* 单位混淆；
* 编造不存在的证据；
* 对相似数字误召回。

采用：

```text
规则 Planner
+ PDF 工具链
+ 结构化 facts
+ 数值归一化
+ 证据校验
+ 拒答机制
```

这种设计更适合高精度数值问答场景。

---



## ✅ 项目总结

本项目完成了一个可运行、可评测、可优化的通用复杂 PDF 精准抽取 Skill。

核心贡献包括：

* ✅ 使用真实复杂 PDF 构建测试集；
* ✅ 实现 PDF 预检、多引擎抽取、结构化索引和证据问答；
* ✅ 针对真实年报中的繁体中文乱码问题加入 fallback；
* ✅ 针对财务表格加入 line-table facts 抽取；
* ✅ 设计 exact match、numeric accuracy、evidence accuracy 和 abstain accuracy 评测指标；
* ✅ 实现不依赖 PI-Agent 的轻量 Agent 执行逻辑。

该 Skill 可迁移到财报、政策、合同、论文、白皮书等复杂文档场景，适合需要高精度、可追溯、可评测 PDF 数据抽取的任务。

---

## 📌 License

This project is released under the MIT License.
