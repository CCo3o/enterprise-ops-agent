"""A small, inspectable incident-analysis workflow.

The workflow is deliberately deterministic in the first milestone. A model can
later replace ``choose_tools`` while the tool contracts and evidence format stay
stable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .tools import get_metric_snapshot, search_docs, search_logs


@dataclass
class AnalysisResult:
    question: str
    plan: list[str]
    findings: list[str]
    evidence: list[dict[str, Any]]
    steps: list[str]
    commands: list[str]
    risk_note: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__


def choose_tools(question: str) -> list[str]:
    """Choose tools from intent; this is the seam for LLM tool selection."""
    q = question.lower()
    tools = ["search_docs"]
    if any(word in q for word in ("日志", "timeout", "500", "错误码", "error", "connection")):
        tools.append("search_logs")
    if any(word in q for word in ("指标", "延迟", "超时", "500", "连接池", "latency")):
        tools.append("get_metric_snapshot")
    return tools


def analyze(question: str, service: str = "order-api") -> AnalysisResult:
    selected = choose_tools(question)
    plan = [f"调用 {name}" for name in selected]
    evidence: list[dict[str, Any]] = []
    findings: list[str] = []

    docs = search_docs(question + " 订单 数据库 连接池", limit=5)
    if "search_docs" in selected:
        for hit in docs:
            evidence.append({"type": "document", "source": hit["source"], "score": hit["score"]})

    logs = search_logs("", service=service) if "search_logs" in selected else []
    timeout_logs = [item for item in logs if any(k in item["message"].lower() for k in ("timeout", "pool exhausted"))]
    for item in timeout_logs:
        evidence.append({"type": "log", "source": "logs.jsonl", "timestamp": item["timestamp"], "trace_id": item["trace_id"], "quote": item["message"]})

    metrics = get_metric_snapshot(service) if "get_metric_snapshot" in selected else {}
    if metrics.get("found"):
        evidence.append({"type": "metric", "source": "metrics.json", "field": "db_pool_in_use/db_pool_size", "value": f"{metrics['db_pool_in_use']}/{metrics['db_pool_size']}"})

    is_follow_up = any(word in question for word in ("先检查", "怎么排查", "排查顺序", "第一步", "下一步"))
    if is_follow_up and timeout_logs and metrics.get("db_pool_in_use") == metrics.get("db_pool_size"):
        findings.append("建议先确认连接池是否持续满载，再检查数据库慢查询和锁等待；当前日志与指标已经支持优先排查连接池。")
    elif timeout_logs and metrics.get("db_pool_in_use") == metrics.get("db_pool_size"):
        findings.append("最可能原因是数据库连接池耗尽，连接获取超时进一步推高接口延迟并导致 500。")
    elif timeout_logs:
        findings.append("日志显示存在数据库连接超时，需要优先检查数据库可用性、连接池和慢查询。")
    else:
        findings.append("当前证据不足以确认根因，需要补充对应时间窗口的应用日志和指标。")

    steps = [
        "确认故障时间窗口内连接池使用数、等待数和数据库连接数。",
        "检查数据库慢查询、锁等待和网络连通性。",
        "核对 order-api 的连接池上限、超时和连接释放逻辑。",
        "修复后观察错误率与 p95 延迟是否恢复。",
    ]
    commands = [
        "kubectl -n production get deploy order-api -o yaml | Select-String 'DB_POOL|TIMEOUT'",
        "kubectl -n production logs deploy/order-api --since=15m | Select-String 'connection|timeout'",
    ]
    return AnalysisResult(question, plan, findings, evidence, steps, commands, "高风险操作仅生成命令，不会自动执行。")
