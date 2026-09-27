"""Run the offline evaluation set and report tool/source recall."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import analyze, choose_tools


def main() -> None:
    cases = json.loads(Path("evaluation/cases.json").read_text(encoding="utf-8"))
    passed = 0
    for case in cases:
        result = analyze(case["question"])
        actual_tools = set(choose_tools(case["question"]))
        sources = {item["source"] for item in result.evidence if item["type"] == "document"}
        ok = set(case["expected_tools"]).issubset(actual_tools) and set(case["expected_sources"]).issubset(sources)
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'} {case['id']} tools={sorted(actual_tools)} sources={sorted(sources)}")
    print(f"score={passed}/{len(cases)}")


if __name__ == "__main__":
    main()
