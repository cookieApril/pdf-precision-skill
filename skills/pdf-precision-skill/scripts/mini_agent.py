#!/usr/bin/env python3
"""Minimal Agent loop for the pdf_precision_skill, independent from PI-Agent.
It is intentionally small: plan -> tool execution -> verification -> final answer.
"""
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ToolRunner:
    def run(self, cmd):
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        return {"cmd": cmd, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

class MiniPDFPrecisionAgent:
    def __init__(self):
        self.runner = ToolRunner()
        self.trace = []

    def answer(self, pdf, query):
        pdf = Path(pdf).resolve()
        out_dir = ROOT / "outputs" / pdf.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        preflight = out_dir / "preflight.json"
        extracted = out_dir / "extract.jsonl"
        index = out_dir / "index.json"

        plan = [
            [sys.executable, "scripts/preflight.py", str(pdf), "--out", str(preflight)],
            [sys.executable, "scripts/extract_pdf.py", str(pdf), "--out", str(extracted)],
            [sys.executable, "scripts/build_index.py", str(extracted), "--out", str(index)],
            [sys.executable, "scripts/answer_query.py", "--index", str(index), "--query", query],
        ]
        final = None
        for cmd in plan:
            result = self.runner.run(cmd)
            self.trace.append(result)
            if result["returncode"] != 0:
                return {"answer":"执行失败", "error":result["stderr"], "trace":self.trace}
            final = result["stdout"]
        try:
            ans = json.loads(final)
        except Exception:
            ans = {"answer": final}
        ans["agent_trace"] = [{"cmd":" ".join(x["cmd"]), "returncode":x["returncode"]} for x in self.trace]
        return ans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("query")
    args = ap.parse_args()
    agent = MiniPDFPrecisionAgent()
    print(json.dumps(agent.answer(args.pdf, args.query), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
