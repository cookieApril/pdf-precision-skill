#!/usr/bin/env python3
"""PDF preflight: determine text availability, scanned pages, metadata and extraction risks."""
import argparse, json, sys
from pathlib import Path
import fitz


def preflight(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    pages = []
    total_text = 0
    total_images = 0
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        images = page.get_images(full=True)
        total_text += len(text.strip())
        total_images += len(images)
        pages.append({
            "page": i,
            "text_chars": len(text.strip()),
            "image_count": len(images),
            "likely_scanned": len(text.strip()) < 30 and len(images) > 0,
            "rotation": page.rotation,
            "width": page.rect.width,
            "height": page.rect.height,
        })
    return {
        "path": str(pdf_path),
        "page_count": len(doc),
        "metadata": doc.metadata,
        "is_encrypted": doc.is_encrypted,
        "total_text_chars": total_text,
        "total_images": total_images,
        "likely_scanned_doc": total_text < max(30, 20 * len(doc)) and total_images > 0,
        "pages": pages,
        "risk_flags": risk_flags(total_text, total_images, pages),
    }


def risk_flags(total_text, total_images, pages):
    flags = []
    if any(p["likely_scanned"] for p in pages):
        flags.append("ocr_required_for_some_pages")
    if total_text == 0:
        flags.append("no_embedded_text")
    if total_images > len(pages) * 3:
        flags.append("image_heavy")
    if any(p["rotation"] != 0 for p in pages):
        flags.append("rotated_pages")
    return flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out")
    args = ap.parse_args()
    result = preflight(args.pdf)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
