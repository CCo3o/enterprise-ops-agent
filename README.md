# Enterprise Ops Agent

面向研发团队的企业知识库与故障排查 Agent。用户描述接口或服务故障后，系统检索技术文档，查询模拟日志和指标，并输出带证据的原因分析、排查步骤与安全命令建议。

这是一个可本地运行的全栈 MVP：FastAPI 提供后端和会话接口，原生 HTML/CSS/JavaScript 提供聊天网页，RAG 使用本地 TF-IDF 向量检索，不依赖在线模型或向量数据库。

## MVP 闭环

```text
问题描述 → 判断任务 → 检索技术文档 → 查询日志 → 综合证据 → 输出排查报告
```

第一阶段只支持一个服务、三类工具和一套离线评测数据：

- `search_docs`：检索 API、部署和数据库文档
- `search_logs`：按服务、时间和关键词过滤日志
- `get_metric_snapshot`：查询模拟的错误率、延迟和连接池指标
- 输出：可能原因、证据、排查步骤、建议命令和风险提示

## 项目结构

```text
app/
  agent.py          # 单 Agent 工作流与工具选择
  tools.py          # RAG、日志、指标工具
  api.py            # FastAPI、/chat、多轮会话
  cli.py            # 命令行调试入口
  static/           # 聊天网页
data/
  documents/        # API、部署、数据库和故障复盘资料
  logs.jsonl        # 模拟结构化日志
  metrics.json      # 模拟指标快照
evaluation/         # 离线评测数据和脚本
tests/              # 自动化测试
```

## 系统架构

```text
浏览器聊天网页 → FastAPI /chat → 会话上下文 → Agent 工作流
                                      ├─ TF-IDF 文档检索（RAG）
                                      ├─ 模拟日志查询
                                      ├─ 模拟指标查询
                                      └─ 证据化故障报告
```

## 开发顺序

1. 先固定故障数据和评测问题，避免边做边改变标准。
2. 先实现三个工具的确定性函数，再接入模型做工具选择。
3. 加入 RAG 检索和引用，要求每条结论带文档或日志证据。
4. 增加 API 和简单网页，最后再做 Agent 工作流和部署。

当前仓库只建立项目边界和数据契约，不会修改上层宠物寄养项目的运行代码。

## 本地运行

无需安装第三方依赖：

```powershell
python -m app.cli "为什么订单接口返回 500？"
# 查看完整 JSON（调试工具调用和证据时使用）
python -m app.cli "为什么订单接口返回 500？" --json
python evaluation/run.py
```

输出包含工具调用计划、结论、文档/日志/指标证据、排查步骤，以及只生成不执行的命令。

运行自动化测试：

```powershell
python -m unittest discover -s tests -v
```

## 启动 Chat API

安装依赖后启动：

```powershell
pip install -r requirements.txt
uvicorn app.api:app --reload
```

打开 `http://127.0.0.1:8000` 使用聊天网页，打开 `http://127.0.0.1:8000/docs` 可调试接口。网页会自动保存会话 ID，支持连续追问和新建会话。

当前 RAG 使用本地 TF-IDF 向量检索，适合离线 MVP。后续可把 `search_docs` 替换为 embedding + Chroma/pgvector，而不改变 Agent 和 API 契约。

网页左侧支持上传 Markdown、TXT 和 PDF；PDF 会提取文字后加入本地知识库，下一次提问即可参与检索。

## 模型模式

默认 `MODEL_PROVIDER=local`，使用可重复的离线规则模式，不需要密钥。接入 OpenAI 兼容模型时，在本地 `.env` 或 Render 环境变量中设置 `MODEL_PROVIDER=openai`、`MODEL_NAME`、`MODEL_BASE_URL` 和 `API_KEY`；模型会从已注册工具中选择需要的工具，并基于证据生成结论。密钥只放在环境变量中，不提交到 GitHub。`/health` 会返回当前模式。

## API 示例

```json
POST /chat
{
  "message": "为什么订单接口返回 500？",
  "session_id": null
}
```

首次请求会返回 `session_id`，后续请求携带相同 ID 即可继续追问。高风险命令只展示，不会自动执行。

## Render 部署

仓库包含 `render.yaml`。在 Render 中连接 GitHub 仓库 `CCo3o/enterprise-ops-agent`，选择 Blueprint 部署即可。部署完成后会获得一个公网网址；本地的 `127.0.0.1` 只对当前电脑有效。

## 当前限制与后续计划

- 当前日志、指标和文档是脱敏的模拟数据，适合作品集演示。
- 会话暂存在内存中，服务重启后会清空；生产环境应接入 Redis 或数据库。
- 当前使用本地 TF-IDF，后续可接入真实 embedding、向量数据库和大模型工具调用。
- 后续增加 PDF 解析、文档上传、权限控制和可观测性。

## 下一步

1. 把 `search_docs` 换成向量检索，并保留 `source` 元数据。
2. 增加 FastAPI `/chat` 接口和会话历史。
3. 用模型替换 `choose_tools`，但限制在已注册工具和结构化参数内。
4. 扩展 20～30 条评测用例，记录检索召回、工具选择和答案证据覆盖率。
