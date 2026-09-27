from __future__ import annotations

import argparse
import json

from .agent import analyze


def main() -> None:
    parser = argparse.ArgumentParser(description="研发故障排查 Agent")
    parser.add_argument("question", nargs="+", help="故障问题")
    parser.add_argument("--json", action="store_true", help="输出完整 JSON，供调试使用")
    args = parser.parse_args()
    result = analyze(" ".join(args.question))
    if args.json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        return
    print("\n故障分析报告")
    print(f"问题：{result.question}")
    print(f"结论：{result.findings[0]}")
    print("\n关键证据：")
    for item in result.evidence[:5]:
        if item["type"] == "document":
            print(f"- 文档：{item['source']}")
        elif item["type"] == "log":
            print(f"- 日志：{item['timestamp']} {item['quote']}")
        else:
            print(f"- 指标：{item['field']} = {item['value']}")
    print("\n建议排查：")
    for index, step in enumerate(result.steps, 1):
        print(f"{index}. {step}")
    print("\n建议命令（仅生成，不自动执行）：")
    for command in result.commands:
        print(f"  {command}")


if __name__ == "__main__":
    main()
