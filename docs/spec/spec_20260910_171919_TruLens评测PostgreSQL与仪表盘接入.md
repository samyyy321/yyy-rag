# TruLens 评测 PostgreSQL 与仪表盘接入设计

## 目标

将 TruLens 评测数据从默认本地 SQLite 切换到项目已运行的 PostgreSQL，并提供独立的 TruLens Dashboard 启动入口；不修改 `src/` 生产 RAG 代码。

## 架构

`src/evaluation/trulens_runner.py` 新增创建 Session 的统一函数。函数读取 `TRULENS_DATABASE_URL`：存在时创建指向 PostgreSQL 的 `TruSession`，不存在时保留现有 SQLite 回退行为。所有评测记录器均调用该函数，禁止直接构造无配置的 `TruSession`。

Dashboard 作为 `RAG-assessment/run_trulens_dashboard.py` 的独立进程启动，复用同一个 Session 创建函数与数据库 URL。因此 Dashboard 与集成评测读写同一批 PostgreSQL 数据，不进入生产服务进程。

## 配置

- `TRULENS_DATABASE_URL`：PostgreSQL SQLAlchemy URL；仅用于评测记录和 Dashboard。
- `TRULENS_DASHBOARD_HOST`：Dashboard 监听地址，默认 `127.0.0.1`。
- `TRULENS_DASHBOARD_PORT`：Dashboard 端口，默认 `8501`。

本地评测使用独立 `trulens` 数据库，不与业务数据表、Milvus 或知识库表混用。未配置数据库 URL 时仍使用 `default.sqlite`，便于无 PostgreSQL 环境执行单元测试。

## 依赖

- `psycopg[binary]`：SQLAlchemy PostgreSQL 驱动。
- `trulens-dashboard`：TruLens 的 Streamlit Dashboard。

继续使用 `trulens-providers-langchain`，禁止引入 `trulens-providers-openai`，以避免将项目 OpenAI SDK 降级到 1.x。

## 数据与安全

- PostgreSQL 中会保存问题、检索上下文、回答、评分与评分理由。
- Dashboard 默认仅监听 `127.0.0.1`，不得默认暴露到局域网或公网。
- 数据库 URL 属于凭据配置，只放入 `.env`，不得输出到日志或写入评测记录。
- 本次不迁移既有 `default.sqlite` 历史记录；从切换后开始向 PostgreSQL 写入新记录。

## 验收标准

1. `src/` 无任何改动。
2. 已配置 PostgreSQL URL 时，TruLens Session 连接 PostgreSQL 并自动创建所需表。
3. 未配置 URL 时，评测仍能回退 SQLite。
4. Dashboard 从同一 PostgreSQL URL 读取记录，默认绑定本地回环地址。
5. 单元测试不依赖真实 PostgreSQL；集成测试验证实际记录可写入 PostgreSQL。

