#!/usr/bin/env python3
"""Evidence-first PDF QA over the local JSON index.

This script is intentionally small and auditable. It first tries structured facts
extracted from line tables, then table cells, then text blocks, and finally abstains.
"""
import argparse, json, re
from pathlib import Path
from normalize import normalize_number, normalize_metric_name


def tokens(text):
    return set(re.findall(r"[\w\u4e00-\u9fff]+", (text or "").lower()))

METRIC_ALIASES = {
    "除税前利润": ["除所得稅前", "除所得税前", "稅前", "税前", "profit before income tax"],
    "非流动资产": ["非流動資產", "非流动资产", "non-current assets"],
    "非流动负债": ["非流動負債", "非流动负债", "non-current liabilities"],
    "收入": ["收入", "營收", "营收", "總收入", "总收入", "revenue"],
    "毛利": ["毛利", "gross profit"],
    "年内利润": ["年內", "年内", "淨利", "净利", "profit", "loss"],
    "总资产": ["總資產", "总资产", "total assets"],
    "流动资产": ["流動資產", "流动资产", "current assets"],
    "总权益": ["總權益", "总权益", "total equity"],
    "总负债": ["總負債", "总负债", "total liabilities"],
    "流动负债": ["流動負債", "流动负债", "current liabilities"],
    "现金及现金等价物": ["現金及現金等價物", "现金及现金等价物", "cash and cash equivalents"],
    "研发开支": ["研發開支", "研发开支", "研發費用", "研发费用", "research and development"],
    "销售成本": ["銷售成本", "销售成本", "cost of sales"],
    "每股基本亏损": ["每股基本", "basic", "每股基本虧損", "每股基本亏损"],
}


def parse_query(q):
    years = re.findall(r"20\d{2}", q)
    ql = q.lower()
    metric = ""
    raw_metric = ""
    for canonical, aliases in METRIC_ALIASES.items():
        for a in aliases:
            if a.lower() in ql:
                metric, raw_metric = canonical, a
                break
        if metric:
            break
    if not metric:
        metric_words = ["补贴上限", "最高补贴", "违约金", "F1", "准确率", "subsidy cap", "liquidated damages", "accuracy"]
        raw_metric = next((m for m in metric_words if m.lower() in ql), "")
        metric = normalize_metric_name(raw_metric)
    return {"years": years, "metric": metric, "raw_metric": raw_metric}


def metric_match(needle, text):
    if not needle:
        return False
    text_l = (text or "").lower()
    if needle.lower() in text_l:
        return True
    for alias in METRIC_ALIASES.get(needle, []):
        if alias.lower() in text_l:
            return True
    return False



def metric_quality(needle, metric_text):
    """Higher score means the row label is a cleaner match for the query metric."""
    if not needle:
        return 0
    m = (metric_text or "").strip().lower()
    aliases = [needle] + METRIC_ALIASES.get(needle, [])
    aliases = [a.lower() for a in aliases]
    for a in aliases:
        if m == a:
            return 100
    for a in aliases:
        if m.startswith(a) and len(m) <= len(a) + 8:
            return 70
    for a in aliases:
        if a in m:
            return 25
    return 0

def score_text(item, q, parsed):
    s = len(tokens(q) & set(item.get("tokens", [])))
    txt = item.get("text", "") + " " + item.get("flat_text", "") + " " + item.get("source_line", "")
    for y in parsed["years"]:
        if y in txt: s += 3
    if parsed["metric"] and metric_match(parsed["metric"], txt): s += 5
    elif parsed["raw_metric"] and parsed["raw_metric"] in txt: s += 4
    return s * item.get("confidence", 0.7)


def find_in_facts(facts, q, parsed):
    hits = []
    for f in facts:
        if parsed["years"] and f.get("year") not in parsed["years"]:
            continue
        mq = metric_quality(parsed["metric"], f.get("metric", "")) if parsed["metric"] else 0
        if parsed["metric"] and mq <= 0:
            continue
        sc = score_text(f, q, parsed) + 5 + mq - min(20, len(str(f.get("metric", ""))) / 3)
        # Section hints reduce ambiguity in repeated annual-report tables.
        page = int(f.get("page") or 0)
        if any(x in q for x in ["財務概要", "财务概要"]):
            sc += 35 if 6 <= page <= 10 else -10
        if any(x in q for x in ["綜合收益表", "综合收益表"]):
            sc += 35 if page == 212 else -10
        if any(x in q for x in ["綜合財務狀況表", "综合财务状况表"]):
            sc += 35 if page in (214, 215) else -10
        if any(x in q for x in ["綜合現金流量表", "综合现金流量表"]):
            sc += 35 if page in (220, 221) else -10
        hits.append((sc, f))
    return sorted(hits, key=lambda x: x[0], reverse=True)


def find_in_tables(tables, q, parsed):
    candidates = []
    for t in tables:
        rows = t.get("rows", [])
        sc = score_text(t, q, parsed)
        if sc <= 0:
            continue
        best_cell = None
        metric_l = (parsed.get("raw_metric") or parsed.get("metric") or "").lower()
        metric_col = None
        header_row = None
        for hr_idx, row in enumerate(rows[:5]):
            for c_idx, cell in enumerate(row):
                cell_l = str(cell or "").lower()
                if metric_l and (metric_l in cell_l or cell_l == metric_l):
                    metric_col, header_row = c_idx, hr_idx
                    break
            if metric_col is not None:
                break
        if metric_col is not None:
            stop = {"what","is","the","of","in","on","a","an","and","year","company","enterprise", "多少", "是多少"}
            q_terms = [x for x in tokens(q) if x not in stop and x not in tokens(metric_l)]
            best_row_score = -1
            for r_idx, row in enumerate(rows):
                if header_row is not None and r_idx <= header_row:
                    continue
                row_text = " ".join(str(c or "") for c in row)
                row_l = row_text.lower()
                if parsed["years"] and not all(y in row_text for y in parsed["years"]):
                    continue
                rs = sum(1 for term in q_terms if term in row_l)
                if rs > best_row_score and metric_col < len(row):
                    cell = row[metric_col]
                    n = normalize_number(cell)
                    if cell not in (None, ""):
                        best_row_score = rs
                        best_cell = {"row": r_idx, "col": metric_col, "raw": cell, "normalized_number": n}
        if best_cell is None:
            for r_idx, row in enumerate(rows):
                row_text = " ".join(str(c or "") for c in row)
                if parsed["metric"] and not metric_match(parsed["metric"], row_text):
                    continue
                if parsed["years"] and not all(y in row_text for y in parsed["years"]):
                    # annual-report line tables may omit the year in each row, so do not hard fail if row has many nums
                    pass
                for c_idx, cell in enumerate(row[1:], start=1):
                    n = normalize_number(cell)
                    if n is not None and str(cell).strip() not in parsed["years"]:
                        best_cell = {"row": r_idx, "col": c_idx, "raw": cell, "normalized_number": n}
                        break
                if best_cell:
                    break
        candidates.append((sc, t, best_cell))
    return sorted(candidates, key=lambda x: x[0], reverse=True)


def answer(index, query):
    parsed = parse_query(query)
    fact_hits = find_in_facts(index.get("facts", []), query, parsed)
    if fact_hits:
        sc, f = fact_hits[0]
        return {
            "query": query,
            "answer": str(f.get("answer")),
            "normalized_answer": normalize_number(f.get("answer")),
            "confidence": round(min(0.97, 0.60 + sc / 25), 3),
            "evidence": [{"page": f.get("page"), "type": "fact", "metric": f.get("metric"), "year": f.get("year"), "source_line": f.get("source_line"), "source": f.get("source")}],
            "audit_trace": {"parsed_query": parsed, "strategy": "fact_first"},
        }

    table_hits = find_in_tables(index.get("tables", []), query, parsed)
    if table_hits and table_hits[0][2]:
        sc, t, cell = table_hits[0]
        return {
            "query": query,
            "answer": str(cell["raw"]),
            "normalized_answer": cell["normalized_number"],
            "confidence": round(min(0.96, 0.55 + sc / 20), 3),
            "evidence": [{"page": t.get("page"), "type": "table", "table_id": t.get("table_id"), "cell": cell, "source": t.get("source")}],
            "audit_trace": {"parsed_query": parsed, "strategy": "table_cell_first"},
        }

    blocks = sorted(index.get("blocks", []), key=lambda b: score_text(b, query, parsed), reverse=True)
    for b in blocks[:8]:
        txt = b.get("text", "")
        if parsed["years"] and not any(y in txt for y in parsed["years"]):
            continue
        if parsed["metric"] and not metric_match(parsed["metric"], txt):
            continue
        n = normalize_number(txt)
        return {
            "query": query,
            "answer": txt[:600],
            "normalized_answer": n,
            "confidence": 0.62 if n is not None else 0.55,
            "evidence": [{"page": b.get("page"), "type": "text", "bbox": b.get("bbox"), "text": txt[:300], "source": b.get("source")}],
            "audit_trace": {"parsed_query": parsed, "strategy": "text_block_fallback"},
        }
    return {"query": query, "answer": "文档中未找到可靠答案", "normalized_answer": None, "confidence": 0.0, "evidence": [], "audit_trace": {"parsed_query": parsed, "strategy": "abstain"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--query", required=True)
    args = ap.parse_args()
    idx = json.loads(Path(args.index).read_text(encoding="utf-8"))
    print(json.dumps(answer(idx, args.query), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
