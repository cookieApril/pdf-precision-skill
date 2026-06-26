#!/usr/bin/env python3
"""Evaluate predictions against a JSONL gold set."""
import argparse, json, math
from pathlib import Path


def load_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def norm(x):
    return str(x).strip().replace(",", "").replace("，", "")


def numeric_close(a, b, rel=0.001):
    try:
        a, b = float(a), float(b)
        if b == 0:
            return abs(a) <= rel
        return abs(a-b)/abs(b) <= rel
    except Exception:
        return False


def evaluate(gold, pred):
    pred_map = {p.get("id") or p.get("query"): p for p in pred}
    rows = []
    for g in gold:
        key = g.get("id") or g.get("query")
        p = pred_map.get(key, {})
        exact = norm(p.get("answer")) == norm(g.get("answer"))
        numeric = numeric_close(p.get("normalized_answer"), g.get("normalized_answer", g.get("answer")))
        evidence_pages = {str(e.get("page")) for e in p.get("evidence", [])}
        gold_pages = {str(x) for x in g.get("evidence_pages", [])}
        evidence_ok = bool(gold_pages) and bool(evidence_pages & gold_pages)
        abstain_ok = g.get("answer") is None and (not p.get("evidence") or "未找到" in str(p.get("answer")))
        rows.append({"id": key, "exact": exact, "numeric": numeric, "evidence": evidence_ok, "abstain": abstain_ok})
    def avg(k): return sum(1 for r in rows if r[k]) / max(1, len(rows))
    return {"count": len(rows), "exact_match": avg("exact"), "numeric_accuracy": avg("numeric"), "evidence_accuracy": avg("evidence"), "abstain_accuracy": avg("abstain"), "details": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()
    result = evaluate(load_jsonl(args.dataset), load_jsonl(args.pred))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
