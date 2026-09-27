"""Optional OpenAI-compatible model gateway.

The project remains runnable offline. When MODEL_PROVIDER=openai and API_KEY is
configured, this module can be used by the orchestration layer to plan tools or
write the final report. Secrets are read only from environment variables.
"""
from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


def enabled() -> bool:
    return os.getenv("MODEL_PROVIDER", "local").lower() != "local" and bool(os.getenv("API_KEY"))


def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    if not enabled():
        raise RuntimeError("模型未启用：请设置 MODEL_PROVIDER、MODEL_NAME 和 API_KEY")
    base_url = os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    payload = {"model": os.environ.get("MODEL_NAME", "gpt-4o-mini"), "messages": messages, "temperature": 0.1}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    request = Request(f"{base_url}/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {os.environ['API_KEY']}"}, method="POST")
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def select_tools(question: str) -> list[str]:
    """Ask the model to select only from the registered diagnostic tools."""
    tools = [
        {"type": "function", "function": {"name": "search_docs", "description": "检索研发技术文档", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}},
        {"type": "function", "function": {"name": "search_logs", "description": "查询服务日志", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}},
        {"type": "function", "function": {"name": "get_metric_snapshot", "description": "查询服务指标快照", "parameters": {"type": "object", "properties": {"service": {"type": "string"}}}}},
    ]
    result = chat([{"role": "system", "content": "根据问题选择需要的诊断工具。只调用必要工具，不要回答问题。"}, {"role": "user", "content": question}], tools)
    calls = result.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
    return [call["function"]["name"] for call in calls if call.get("function", {}).get("name") in {"search_docs", "search_logs", "get_metric_snapshot"}]


def embeddings(texts: list[str]) -> list[list[float]]:
    if not enabled():
        raise RuntimeError("模型未启用")
    base_url = os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    payload = {"model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"), "input": texts}
    request = Request(f"{base_url}/embeddings", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {os.environ['API_KEY']}"}, method="POST")
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode())["data"]
    return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
