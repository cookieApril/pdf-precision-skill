# pdf_precision_skill

这是一个复杂 PDF 高精度抽取与分析 skill。它支持政策、合同、论文、技术文档、扫描件和多文档对比等场景。

## 目录

- `SKILL.md`：skill 说明与工作流。
- `configs/default.yaml`：默认抽取与评测配置。
- `scripts/preflight.py`：PDF 预检。
- `scripts/extract_pdf.py`：多引擎抽取。
- `scripts/build_index.py`：结构化索引构建。
- `scripts/answer_query.py`：证据优先问答。
- `scripts/evaluate.py`：评测脚本。
- `scripts/make_eval_set.py`：自主构建测试集。
- `scripts/mini_agent.py`：不依赖 PI-Agent 的原始 Agent 执行逻辑。

## Demo

```bash
python scripts/make_eval_set.py --out tests/eval_set
python scripts/mini_agent.py tests/eval_set/sample_policy.pdf "2024年企业A补贴上限是多少？"
```

## Meituan 2025 annual-report dataset

This delivery uses the uploaded Meituan 2025 annual report as the main evaluation dataset.

```bash
python scripts/make_meituan_eval_set.py \
  --source-pdf /path/to/20260424065602215412120050_tc.pdf \
  --out tests/eval_set

python scripts/extract_pdf.py tests/eval_set/meituan_2025_annual_report_tc.pdf \
  --out examples/meituan_run/extracted.jsonl
python scripts/build_index.py examples/meituan_run/extracted.jsonl \
  --out examples/meituan_run/index.json
python scripts/answer_query.py --index examples/meituan_run/index.json \
  --query "2025年美团收入是多少"
```

The dataset contains 30 gold questions covering financial-summary tables, segment tables, formal statements, metadata lookup, derived calculations, and negative abstain cases.
