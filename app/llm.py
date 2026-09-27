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
