#!/usr/bin/env python3
"""Ensemble PDF extractor. Outputs JSONL blocks with text, tables, line tables and facts.

Design goal: be robust on complex annual reports where embedded fonts may break
PyMuPDF/pdfplumber Chinese extraction. The extractor therefore combines:
1) PyMuPDF block extraction (fast, includes bboxes);
2) pdfplumber word/table extraction when available;
3) poppler pdftotext fallback, which often recovers CJK text better;
4) simple line-table fact extraction for annual-report style tables.
"""
import argparse, json, re, subprocess, tempfile
from pathlib import Path
import fitz
import pdfplumber


def looks_garbled(text: str) -> bool:
    if not text:
        return True
    bad = text.count("�") + text.count("(cid:") + sum(1 for ch in text if "\u0300" <= ch <= "\u036f")
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    return bad > 10 or (len(text) > 80 and cjk < 3 and bad > 0)


def run_pdftotext(pdf_path):
    """Return page texts from poppler pdftotext -layout. Empty list if unavailable."""
    try:
        proc = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=120
        )
        out = proc.stdout.decode("utf-8", errors="ignore")
        if not out.strip():
            return []
        return out.split("\f")
    except Exception:
        return []


def extract_text_blocks(pdf_path):
    doc = fitz.open(pdf_path)
    doc_id = Path(pdf_path).stem
    for page_no, page in enumerate(doc, start=1):
        blocks = page.get_text("blocks")
        page_text = page.get_text("text") or ""
        if looks_garbled(page_text):
            # Keep bboxes if possible, but mark confidence lower; pdftotext will add clean page text.
            conf = 0.45
        else:
            conf = 0.86
        for b in blocks:
            x0, y0, x1, y1, text, block_no, block_type = b[:7]
            text = re.sub(r"\s+", " ", text or "").strip()
            if text:
                yield {
                    "doc_id": doc_id, "page": page_no, "type": "text",
                    "text": text, "bbox": [x0, y0, x1, y1],
                    "source": "pymupdf", "confidence": conf,
                }


def extract_pdftotext_pages(pdf_path):
    doc_id = Path(pdf_path).stem
    for page_no, text in enumerate(run_pdftotext(pdf_path), start=1):
        text = text.strip("\n")
        if text.strip():
            yield {
                "doc_id": doc_id, "page": page_no, "type": "text",
                "text": text, "bbox": None, "source": "pdftotext-layout", "confidence": 0.92,
            }


def extract_words(pdf_path):
    doc_id = Path(pdf_path).stem
    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(use_text_flow=True, keep_blank_chars=False) or []
            if words:
                yield {
                    "doc_id": doc_id, "page": page_no, "type": "words",
                    "words": words, "source": "pdfplumber", "confidence": 0.72,
                }


def extract_tables_pdfplumber(pdf_path):
    doc_id = Path(pdf_path).stem
    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            try:
                tables = page.extract_tables() or []
            except Exception:
                tables = []
            for idx, table in enumerate(tables, start=1):
                clean = [[cell.strip() if isinstance(cell, str) else cell for cell in row] for row in table if row]
                if clean:
                    yield {
                        "doc_id": doc_id, "page": page_no, "type": "table",
                        "table_id": f"p{page_no}_plumber_t{idx}", "rows": clean,
                        "bbox": None, "source": "pdfplumber", "confidence": 0.76,
                    }


def extract_tables_camelot(pdf_path):
    doc_id = Path(pdf_path).stem
    try:
        import camelot
        tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="stream")
    except Exception:
        return []
    out = []
    for idx, t in enumerate(tables, start=1):
        try:
            rows = t.df.fillna("").values.tolist()
            page_no = int(t.page)
            acc = float(t.parsing_report.get("accuracy", 70)) / 100.0
            out.append({
                "doc_id": doc_id, "page": page_no, "type": "table",
                "table_id": f"p{page_no}_camelot_t{idx}", "rows": rows,
                "bbox": None, "source": "camelot", "confidence": min(0.95, max(0.55, acc)),
            })
        except Exception:
            continue
    return out

NUM_RE = re.compile(r"\(?-?\d[\d,]*\)?(?:\.\d+)?")
YEAR_RE = re.compile(r"20\d{2}")


def normalize_num_text(s):
    return (s or "").replace(" ", "").replace("，", ",")


def extract_line_table_facts_from_text(pdf_path):
    """Extract facts from lines like: 收入 179,127,997 ... 364,854,746.
    This is intentionally conservative: only emits facts when a page has year headers
    and a row has the same number of numeric cells as years.
    """
    doc_id = Path(pdf_path).stem
    for page_no, text in enumerate(run_pdftotext(pdf_path), start=1):
        lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
        page_years = []
        for ln in lines[:60]:
            ys = YEAR_RE.findall(ln)
            if len(ys) >= 2:
                page_years = ys[-5:]  # annual reports often have 5-year tables
                break
        if not page_years:
            continue
        table_rows = []
        for ln in lines:
            nums = NUM_RE.findall(ln)
            if len(nums) < 2:
                continue
            # Remove numbers that are just years from candidate numeric cells.
            value_nums = [n for n in nums if not YEAR_RE.fullmatch(n.strip("()"))]
            if len(value_nums) < 2:
                continue
            metric = NUM_RE.split(ln, maxsplit=1)[0].strip(" ：:•\t")
            metric = re.sub(r"\s+", " ", metric)
            if not metric or len(metric) > 60:
                continue
            table_rows.append([metric] + value_nums)
            if len(value_nums) == len(page_years):
                for y, val in zip(page_years, value_nums):
                    yield {
                        "doc_id": doc_id, "page": page_no, "type": "fact",
                        "metric": metric, "year": y, "answer": val,
                        "source_line": ln.strip(), "source": "pdftotext-line-table", "confidence": 0.88,
                    }
        if table_rows:
            yield {
                "doc_id": doc_id, "page": page_no, "type": "table",
                "table_id": f"p{page_no}_line_table", "rows": table_rows,
                "bbox": None, "source": "pdftotext-line-table", "confidence": 0.80,
            }


def extract_pdf(pdf_path):
    pdf_path = Path(pdf_path)
    items = []
    items.extend(extract_text_blocks(pdf_path))
    items.extend(extract_pdftotext_pages(pdf_path))
    items.extend(extract_words(pdf_path))
    items.extend(extract_tables_pdfplumber(pdf_path))
    # Camelot is useful for small PDFs, but very slow on hundreds-page reports; enable explicitly.
    import os
    if os.environ.get("PDF_PRECISION_ENABLE_CAMELOT", "0") == "1":
        items.extend(extract_tables_camelot(pdf_path))
    items.extend(extract_line_table_facts_from_text(pdf_path))
    return sorted(items, key=lambda x: (x.get("page", 0), x.get("type", ""), x.get("table_id", "")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for item in extract_pdf(args.pdf):
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"wrote {args.out}")

if __name__ == "__main__":
    main()
