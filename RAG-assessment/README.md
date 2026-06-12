# RAG-assessment

这是项目的独立 RAG 评测入口目录。TruLens 运行时实现位于 `src/evaluation/`，本目录只放评测执行脚本、Dashboard 启动入口和评测数据。

## 目录结构

```text
src/evaluation/
├── trulens_doc_rag_adapter.py  # RAG 评测适配器
├── trulens_runner.py           # TruLens Session、指标与记录器
└── trulens_dashboard.py        # Dashboard 配置与启动命令

RAG-assessment/
├── README.md
├── run_trulens_evaluation.py   # 执行评测集
├── run_trulens_dashboard.py    # 启动 Dashboard
└── data/doc_rag_eval.jsonl     # 评测问题集
```

## 环境准备

在项目根目录执行：

```powershell
python -m pip install -r requirements.txt
```

`.env` 中需要配置：

```env
TRULENS_DATABASE_URL=postgresql+psycopg://rag:rag@localhost:5432/trulens
TRULENS_DASHBOARD_HOST=127.0.0.1
TRULENS_DASHBOARD_PORT=8501
```

## 执行评测

评测入口要求设置 `RUN_TRULENS_EVAL=1`，以避免普通运行误触发远程模型调用。

只评测第一条样本：

```powershell
$env:PYTHONPATH = (Get-Location).Path
$env:RUN_TRULENS_EVAL = "1"
$env:TRULENS_CASE_LIMIT = "1"
python RAG-assessment/run_trulens_evaluation.py
```

运行全部评测样本：

```powershell
$env:TRULENS_CASE_LIMIT = "0"
python RAG-assessment/run_trulens_evaluation.py
```

评测集位于：

```text
RAG-assessment/data/doc_rag_eval.jsonl
```

每条样本会同步等待当前 record 的三项指标：

- Context Relevance
- Answer Relevance
- Groundedness

评测结果写入 PostgreSQL 的 `trulens` 数据库。

## 启动 Dashboard

先确保 PostgreSQL 已启动：

```powershell
docker compose up -d postgres
```

然后在另一个 PowerShell 窗口执行：

```powershell
python RAG-assessment/run_trulens_dashboard.py
```

浏览器打开：

```text
http://127.0.0.1:8501
```

Dashboard 只读取 PostgreSQL 中已有的 TruLens 数据，不会主动执行 RAG 评测。

## 本地测试

评测单元测试不调用 DashScope、Milvus 或 PostgreSQL：

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m pytest test/evaluation -q --basetemp .pytest_tmp
```

## 安全与成本

- 真实评测会把问题、检索上下文和回答发送给配置的 DashScope 裁判模型。
- 每条样本会产生 RAG 与三项裁判指标的模型调用成本。
- 不要将敏感数据、API Key、Token 或内部机密写入评测集。
- Dashboard 默认绑定 `127.0.0.1`，不应直接暴露到公网。

