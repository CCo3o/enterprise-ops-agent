"""Run the offline evaluation set and report tool/source recall."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import analyze, choose_tools


def main() -> None:
    cases = json.loads(Path("evaluation/cases.json").read_text(encoding="utf-8"))
    passed = tool_hits = source_hits = answer_hits = 0
    for case in cases:
        result = analyze(case["question"])
        actual_tools = set(choose_tools(case["question"]))
        sources = {item["source"] for item in result.evidence if item["type"] == "document"}
        tool_ok = set(case["expected_tools"]).issubset(actual_tools)
        source_ok = set(case["expected_sources"]).issubset(sources)
        answer_ok = all(keyword in result.findings[0] for keyword in case.get("expected_keywords", []))
        tool_hits += tool_ok
        source_hits += source_ok
        answer_hits += answer_ok
        ok = tool_ok and source_ok and answer_ok
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'} {case['id']} tool={tool_ok} source={source_ok} answer={answer_ok}")
    total = len(cases)
    print(f"tool_accuracy={tool_hits/total:.1%}")
    print(f"source_recall={source_hits/total:.1%}")
    print(f"answer_keyword_accuracy={answer_hits/total:.1%}")
    print(f"overall={passed}/{total} ({passed/total:.1%})")


if __name__ == "__main__":
    main()
