# TruLens 评测 PostgreSQL 与仪表盘接入任务

关联设计文档：`docs/spec/spec_20260910_171919_TruLens评测PostgreSQL与仪表盘接入.md`

## 任务状态

- [x] 新增 PostgreSQL 与 Dashboard 依赖及配置样例。
- [x] 新增可回退 SQLite 的 TruLens Session 工厂。
- [x] 新增 Dashboard 启动入口与参数校验。
- [x] 以 TDD 新增并验证 Session、Dashboard 配置单元测试。
- [x] 创建并验证 PostgreSQL `trulens` 数据库连接与实际评测写入。
- [x] 更新运行说明、完成验证记录；不执行 Git 提交。

## 任务 1：配置与依赖

**文件：** 修改 `requirements-evaluation.txt`、`.env.example`，新增或更新 `.env` 中本地配置。

- [x] 添加 `psycopg[binary]` 与 `trulens-dashboard`。
- [x] 增加三项 `TRULENS_*` 配置；Dashboard 默认仅绑定 `127.0.0.1`。

## 任务 2：评测持久化与 Dashboard

**文件：** 修改 `src/evaluation/trulens_runner.py`，新增 `RAG-assessment/run_trulens_dashboard.py`。

- [x] 从 `TRULENS_DATABASE_URL` 创建 Session；URL 缺失时回退 SQLite。
- [x] 记录器使用统一 Session 工厂。
- [x] Dashboard 复用统一 Session，并校验端口和监听地址。

## 任务 3：测试与 PostgreSQL 验证

**文件：** 修改 `test/evaluation/test_trulens_doc_rag_adapter.py`，修改 `test/integration/test_trulens_doc_rag.py`。

- [x] 先增加失败测试，覆盖 PostgreSQL URL 选择和 Dashboard 参数。
- [x] 单元测试使用依赖注入，不连接真实 PostgreSQL。
- [x] 执行一条真实评测，确认 PostgreSQL 存在 TruLens 记录。

## 任务 4：说明与收尾

**文件：** 更新 `RAG-assessment/README.md` 与本任务文档。

- [x] 说明安装、建库、评测和 Dashboard 命令。
- [x] 标记每项已完成并写入验证结果。
- [x] 不执行 Git 提交；由用户决定是否提交。

## 验证记录

- [x] PostgreSQL 容器健康运行；已创建独立数据库 `trulens`。
- [x] 应用评测环境已安装 `psycopg[binary]`；`pip check` 无依赖冲突。
- [x] `create_trulens_session()` 已验证连接 `postgresql+psycopg://...@localhost:5432/trulens`，TruLens 已自动创建 `trulens_` 前缀表。
- [x] 在 PostgreSQL 配置下运行一条真实文档 RAG 评测：`test_doc_rag_with_trulens` 通过，追踪记录、检索上下文和回答已写入 `trulens_events`。
- [x] Dashboard 独立 Conda 环境 `yyy-rag-trulens-dashboard` 已创建；`python -m trulens.dashboard --find` 已验证能够发现同一 PostgreSQL 数据库和 `trulens_` 表前缀。
- [x] `python -m pytest test/evaluation -q --basetemp .pytest_tmp`：12 passed。
- [x] `git diff --name-only -- src`：无输出，确认未修改生产代码。

## 已知限制

- `trulens-dashboard==2.14.0` 依赖 `psutil<6`，与应用环境 `unstructured` 的 `psutil>=7.2.2` 冲突，因此 Dashboard 必须在独立环境启动。
- TruLens 2.x 的 OTel 评分为异步任务。评测请求已确保追踪记录落入 PostgreSQL，但 pytest 不会无限等待历史评分任务完成；Dashboard 中评分列可能在后台任务完成前为空。
- 本次不迁移历史 `default.sqlite` 数据。
- 未执行 Git 提交，是否提交由用户决定。


