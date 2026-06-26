---
name: pdf_precision_skill
description: 通用复杂 PDF 的高精度数据提取与分析 skill，支持文本、表格、指标问答、跨文档对比、证据定位与可评测闭环。
---

# pdf_precision_skill

## 目标
面向通用复杂 PDF 文档。典型文档包括：财报、招股书、合同、技术白皮书、政策文件、论文、扫描件、带合并单元格的表格、跨页表格、图文混排文件。

Skill 的核心目标是：

1. 先理解 PDF 结构，再抽取数据。
2. 对答案给出页码、区域、原文证据。
3. 对表格、数字、单位、年份、主体名称进行一致性校验。
4. 支持单文档问答和跨文档指标对比。
5. 用可复现测试集持续评测和优化。

## 适用查询

- “2024 年 A 公司研发费用是多少？”
- “合同里违约金条款如何约定？”
- “这两份政策文件对补贴对象的定义有什么不同？”
- “论文实验表中模型 X 在数据集 Y 上的 F1 是多少？”
- “跨三个 PDF 汇总 2022-2024 年收入、利润、员工数。”

## 工作流

### 1. PDF 预检
使用 `scripts/preflight.py` 判断：

- 是否扫描件；
- 是否加密；
- 页数、字体、图片数量；
- 是否存在可抽取文本；
- 是否需要 OCR；
- 是否可能包含复杂表格。

### 2. 多通道抽取
使用 `scripts/extract_pdf.py` 执行集成抽取：

- PyMuPDF：文本块、字符、坐标、图片、基础结构；
- pdfplumber：词级坐标、表格候选、裁剪区域；
- Camelot/Tabula：矢量表格候选；
- OCR fallback：扫描页或低文本密度页面。

输出统一为 JSONL：

```json
{"doc_id":"...","page":1,"type":"text","text":"...","bbox":[x0,y0,x1,y1],"confidence":0.93}
{"doc_id":"...","page":3,"type":"table","table_id":"p3_t1","rows":[...],"bbox":[...],"confidence":0.88}
```

### 3. 结构化索引
使用 `scripts/build_index.py` 将抽取结果组织为：

- page index；
- section index；
- table index；
- entity/metric index；
- evidence index。

### 4. 精准问答
使用 `scripts/answer_query.py`：

1. 解析问题中的主体、年份、指标、单位、约束；
2. 检索候选页、候选段落、候选表格；
3. 进行字段归一化和数值校验；
4. 如果答案来自表格，优先返回单元格证据；
5. 如果跨文档，先文档内求证，再跨文档合并；
6. 输出 answer + evidence + confidence + audit_trace。

### 5. 评测闭环
使用 `scripts/evaluate.py` 对自主构建测试集进行评测：

- exact_match：标准答案完全一致；
- numeric_accuracy：数值误差是否小于阈值；
- evidence_accuracy：页码/表格/文本证据是否命中；
- table_cell_accuracy：表格单元格定位是否正确；
- abstain_accuracy：文档不存在答案时是否拒答；
- cross_doc_accuracy：跨文档聚合是否正确。

## 精度优化策略

1. 表格双引擎交叉验证：pdfplumber 与 Camelot/Tabula 不一致时进入复核策略。
2. 数字规范化：支持中文数字、千分位、百分号、亿元/万元/元单位换算。
3. 上下文约束：年份、主体、指标名必须与问题同时满足。
4. 证据优先：不能定位证据时降低置信度，不直接编造答案。
5. 负例拒答：测试集中加入“文档没有答案”的问题。
6. 跨页表格拼接：根据表头相似度、页码连续性、列数一致性合并。
7. 渲染核验：必要时将页面渲染为图片，用 bbox 进行人工或模型校验。

## 快速运行

```bash
cd skills/pdf_precision_skill
python scripts/make_eval_set.py --out tests/eval_set
python scripts/preflight.py tests/eval_set/sample_policy.pdf
python scripts/extract_pdf.py tests/eval_set/sample_policy.pdf --out outputs/sample_policy.jsonl
python scripts/build_index.py outputs/sample_policy.jsonl --out outputs/sample_policy.index.json
python scripts/answer_query.py --index outputs/sample_policy.index.json --query "2024年企业A补贴上限是多少？"
python scripts/evaluate.py --dataset tests/eval_set/questions.jsonl --pred outputs/predictions.jsonl
```

## Agent 执行逻辑
Bonus 版本见 `scripts/mini_agent.py`，它不依赖 PI-Agent，采用轻量 ReAct 循环：

- Planner：拆解任务；
- Tool Router：选择 preflight/extract/index/query/evaluate；
- Executor：运行工具；
- Verifier：检查证据和数值一致性；
- Memory：保存中间状态和 audit trace。

## Real-document evaluation dataset

The included primary dataset is based on `tests/eval_set/meituan_2025_annual_report_tc.pdf`, a 345-page Traditional Chinese annual report. Use `scripts/make_meituan_eval_set.py` to regenerate the dataset from a source PDF. The extraction pipeline includes a `pdftotext -layout` fallback and line-table fact extraction because this real PDF exposes CJK font-encoding issues in some native PDF parsers.
