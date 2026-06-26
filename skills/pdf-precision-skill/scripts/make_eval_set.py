#!/usr/bin/env python3
"""Create a small synthetic evaluation set with complex-document patterns."""
import argparse, json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


def setup_styles():
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    for st in styles.byName.values():
        st.fontName = "STSong-Light"
    return styles

def build_policy_pdf(path):
    styles = setup_styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = [Paragraph("Enterprise Support Policy (Synthetic Complex PDF)", styles["Title"]), Spacer(1, 12)]
    story += [Paragraph("Chapter 1 General Rules: This policy applies to registered technology enterprises.", styles["BodyText"]), Spacer(1, 12)]
    data = [["Year", "Enterprise", "Subsidy Cap", "Notes"], ["2023", "Company A", "800000 yuan", "Audit required"], ["2024", "Company A", "1200000 yuan", "No duplicate application"], ["2024", "Company B", "600000 yuan", "Startup priority"]]
    t = Table(data, colWidths=[70, 100, 100, 220])
    t.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.5, colors.black), ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)]))
    story += [t, PageBreak(), Paragraph("Chapter 2 Application Materials: enterprises should submit license, audit report and project description. Liquidated damages are 10% of the subsidy amount.", styles["BodyText"])]
    doc.build(story)


def build_research_pdf(path):
    styles = setup_styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = [Paragraph("Model Experiment Report (Synthetic Research PDF)", styles["Title"]), Spacer(1, 12), Paragraph("This report compares different models on multiple datasets.", styles["BodyText"])]
    data = [["模型", "数据集", "Accuracy", "F1"], ["BaseNet", "Data-A", "0.842", "0.817"], ["PrecisionAgent", "Data-A", "0.913", "0.901"], ["PrecisionAgent", "Data-B", "0.887", "0.872"]]
    t = Table(data, colWidths=[130, 110, 90, 90])
    t.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.5, colors.black), ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)]))
    story += [Spacer(1, 12), t]
    doc.build(story)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    build_policy_pdf(out / "sample_policy.pdf")
    build_research_pdf(out / "sample_research.pdf")
    questions = [
        {"id":"q1", "doc":"sample_policy.pdf", "query":"What is the subsidy cap of Company A in 2024?", "answer":"1200000 yuan", "normalized_answer":1200000, "evidence_pages":[1], "type":"table_numeric"},
        {"id":"q2", "doc":"sample_policy.pdf", "query":"What is the liquidated damages ratio?", "answer":"10%", "normalized_answer":0.1, "evidence_pages":[2], "type":"text_numeric"},
        {"id":"q3", "doc":"sample_research.pdf", "query":"What is the F1 of PrecisionAgent on Data-A?", "answer":"0.901", "normalized_answer":0.901, "evidence_pages":[1], "type":"table_cell"},
        {"id":"q4", "doc":"sample_research.pdf", "query":"What is the subsidy cap of Company A in 2024?", "answer":None, "normalized_answer":None, "evidence_pages":[], "type":"negative_abstain"}
    ]
    with open(out / "questions.jsonl", "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"wrote eval set to {out}")

if __name__ == "__main__":
    main()
