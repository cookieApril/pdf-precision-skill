#!/usr/bin/env python3
"""Build lightweight searchable indexes from extracted JSONL."""
import argparse, json, re
from pathlib import Path


def tokenize(text):
    return [t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", text or "")]


def build_index(jsonl_path):
    blocks, tables, pages, facts = [], [], {}, []
    for line in Path(jsonl_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        p = str(item.get("page"))
        if item.get("type") == "text":
            item["tokens"] = tokenize(item.get("text", ""))
            blocks.append(item)
            pages.setdefault(p, "")
            pages[p] += "\n" + item.get("text", "")
        elif item.get("type") == "table":
            flat = "\n".join("\t".join(str(c or "") for c in row) for row in item.get("rows", []))
            item["flat_text"] = flat
            item["tokens"] = tokenize(flat)
            tables.append(item)
        elif item.get("type") == "fact":
            item["tokens"] = tokenize(" ".join(str(item.get(k,"")) for k in ["metric","year","answer","source_line"]))
            facts.append(item)
    return {"blocks": blocks, "tables": tables, "facts": facts, "pages": pages}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    index = build_index(args.jsonl)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")

if __name__ == "__main__":
    main()
