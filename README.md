# YYY-RAG

YYY-RAG 是一个支持文档 RAG、GraphRAG、NL2SQL 和多通道融合的知识问答系统。系统提供知识库与文档管理、统一流式智能问答、Neo4j 演示图谱、PostgreSQL 运营演示数据，以及 TruLens 评测能力。

## 主要能力

- 知识库创建、查询、更新、删除与分页；
- PDF、DOCX、TXT、Markdown 文档上传、用户可选切分策略、异步导入和状态跟踪；
- MinerU / LlamaIndex 文档解析、Embedding、Milvus 检索与重排；
- `document` 文档知识库、`graph` 医学知识图谱、`sql` 运营数据库三类检索通道；
- 单通道回答与 `asyncio.gather()` 多通道并行检索、融合回答；
- SSE 流式问答；
- React 统一智能问答页面，按通道条件显示知识库选择；
- PostgreSQL、MinIO、Milvus 健康检查；
- TruLens RAG 评测和 Dashboard。

## 技术栈

```text
FastAPI             后端 API、条件通道校验与 SSE 输出
React + Vite        知识库管理与统一智能问答前端
TanStack Query      前端服务端状态与知识库列表缓存
PostgreSQL          知识库业务数据和 NL2SQL 运营演示表
MinIO               原始文档存储
Milvus              文档向量存储和检索
Neo4j               GraphRAG 演示图谱
DashScope           Embedding、Rerank、LLM
MinerU              可选文档解析服务
TruLens             RAG 评测
```

## 目录

```text
app/                React + Vite 前端
src/                FastAPI、RAG、GraphRAG、NL2SQL 与多通道编排
scripts/            运营表和 Neo4j 图谱演示数据初始化脚本
scripts/data/       可审阅的演示图谱 JSON 数据
test/               后端测试
alembic/            数据库迁移
RAG-assessment/     TruLens 评测入口和评测集
docs/               设计、任务和维护文档
docker-compose.yaml 本地基础设施编排
requirements.txt    Python 依赖
.env.example        后端配置模板
```

## 启动前准备

### 1. 激活 Conda 环境

```powershell
conda activate yyy-rag
```

### 2. 准备环境变量

```powershell
Copy-Item .env.example .env
```

至少确认以下配置与实际服务一致：

```env
API_KEY=your-api-key
BASE_URL_CHAT=https://dashscope.aliyuncs.com/compatible-mode/v1
DATABASE_URL=postgresql+psycopg://rag:rag@localhost:5432/rag
MILVUS_URI=http://localhost:19530
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
NEO4J_DATABASE=neo4j
```

`.env` 包含密钥和本地连接信息，不应提交到 Git。

### 3. 启动基础设施

```powershell
docker compose up -d
```

查看状态：

```powershell
docker compose ps
```

文档通道需要 PostgreSQL、MinIO、Milvus；图谱通道需要 Neo4j；SQL 通道需要 PostgreSQL。
### 4. 执行数据库迁移

```powershell
python -m alembic upgrade head
```

### 5. 初始化 GraphRAG / NL2SQL 演示数据

初始化 NL2SQL 所需的运营演示表：

```powershell
python -m scripts.init_operational_tables
```

初始化 GraphRAG 所需的 Neo4j 演示图谱：

```powershell
python -m scripts.init_medical_graph
```

演示图谱数据位于 `scripts/data/medical_graph_demo.json`。其中所有节点、关系和属性只用于验证查询、融合和界面流程，**不能作为医疗诊断、处方、治疗或健康建议依据**。

### 6. 启动后端

```powershell
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --reload
```

Swagger 文档：

```text
http://127.0.0.1:8080/docs
```

健康检查：

```powershell
curl http://127.0.0.1:8080/api/v1/health
```

> 健康检查会验证 PostgreSQL、MinIO 和 Milvus；即使只计划使用 graph/sql 通道，也可能因 Milvus 未启动返回不可用。实际 graph/sql 问答请求不会初始化 Milvus 或 Embedding。

### 7. 启动前端

另开一个终端：

```powershell
cd app
npm install
npm run dev
```

后续开发只需：

```powershell
cd app
npm run dev
```

前端开发服务器会把 `/api` 代理到后端。可复制 `app/.env.example` 为 `app/.env.local`，通过 `VITE_DEV_API_TARGET` 调整代理目标；该本地文件会被 Git 忽略。

## 使用方式

### 知识库管理

在“知识库管理”页面创建知识库、上传文档并等待导入完成。该页面只负责知识库和文档管理，不提供聊天入口。

### 文档切分策略

上传文档时可通过 multipart 字段 `chunk_strategy` 选择切分方式：

| 策略 | 值 | 行为 |
|---|---|---|
| 递归切分 | `recursive` | 默认策略，优先按中文段落、换行和句末边界切分，必要时按更细分隔符递归降级 |
| 滑动窗口 | `sliding_window` | 按固定字符窗口切分，相邻窗口保留系统配置的 overlap |
| 语义切分 | `semantic` | 基于相邻文本单元 Embedding 相似度形成边界，单个过长单元回退递归切分 |

上传示例：

```text
file             必填
category         可选，默认 default
chunk_strategy   可选，默认 recursive
```

用户选择策略，不输入任意切分参数。以下参数由后端环境变量统一管理：

```env
CHUNK_SIZE=512
CHUNK_OVERLAP=64
SEMANTIC_SIMILARITY_THRESHOLD=0.65
```

策略会持久化在文档的 `chunk_strategy` 字段中，后台导入任务按该值执行。调整环境参数或策略只影响之后新导入的文档；已有文档不会自动重新切分或重建向量。

语义切分会额外调用一次 Embedding 计算候选单元的相邻相似度，因此导入速度更慢，且可能增加 Embedding 调用成本。

### 统一智能问答

在“智能问答”页面选择一个或多个通道：

| 通道 | 是否需要知识库 | 数据来源 |
|---|---|---|
| `document` | 是 | 当前知识库中的 Milvus 文档检索 |
| `graph` | 否 | Neo4j 医学知识图谱演示数据 |
| `sql` | 否 | PostgreSQL 运营演示表 |

- 仅选择 `document` 时，必须从下拉框选择知识库；
- 仅选择 `graph`、仅选择 `sql` 或选择二者时，不显示知识库选择器；
- 同时选择多个通道时，后端使用 `asyncio.gather()` 并行收集证据并融合回答；
- 回答正文支持 `**加粗**` Markdown 标记；
- HyDE、粗检索数量和重排数量只在选择 document 通道时显示；回答角色适用于所有通道。

## Chat API

接口路径保持不变：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/chat` | 非流式问答，返回完整回答和 document 通道来源字段 |
| POST | `/api/v1/chat/stream` | SSE 流式问答，统一聊天页使用 |

纯 GraphRAG 请求：

```json
{
  "question": "演示高血压有哪些相关信息？",
  "channels": ["graph"]
}
```

文档和图谱融合请求：

```json
{
  "knowledge_base_id": "知识库 UUID",
  "question": "请综合文档和图谱回答问题",
  "channels": ["document", "graph"]
}
```

`channels` 省略时默认等于：

```json
["document"]
```

只要 `channels` 包含 `document`，`knowledge_base_id` 就是必填字段。GraphRAG/NL2SQL 生成的查询仅允许受限的只读 SQL/Cypher；失败时各最多重试一次。
## 测试

### 后端直接相关测试

使用 Conda `yyy-rag` 环境执行：

```powershell
conda run --no-capture-output -n yyy-rag python -m pytest test/unit/test_multi_channel_schema.py test/unit/test_query_safety.py test/unit/test_graph_rag.py test/unit/test_sql_rag.py test/unit/test_multi_channel.py test/unit/test_chat_service.py test/unit/test_init_scripts.py test/unit/test_chunking.py test/unit/test_doc_ingestion.py test/unit/test_document_service.py test/unit/test_api_schemas.py test/unit/test_db_models.py test/integration/test_api_routes.py -q -p no:cacheprovider
```

这些测试使用模拟对象验证通道选择、只读安全校验、一次重试、初始化脚本意图和接口契约，不会连接真实 LLM、Neo4j、PostgreSQL 或 Milvus。

### 前端测试与构建

```powershell
cd app
npm run test
npm run build
```

前端测试使用模拟 API，不要求启动后端或基础设施。生产构建会执行 TypeScript 检查。

## TruLens 评测

```powershell
$env:PYTHONPATH = (Get-Location).Path
$env:RUN_TRULENS_EVAL = "1"
$env:TRULENS_CASE_LIMIT = "1"
python RAG-assessment/run_trulens_evaluation.py
```

TruLens 评测链路仍基于文档 RAG。图谱、SQL 和多通道融合的评测不属于当前评测集范围。

## Git 忽略与本地清理

应保留在 Git 中：

```text
app/ 源码、package.json、package-lock.json、app/.env.example
scripts/ 源码和 scripts/data/medical_graph_demo.json
src/、test/、alembic/、docs/、requirements.txt、.env.example
```

已忽略的本地产物包括：

```text
app/node_modules/
app/dist/
app/*.tsbuildinfo
app/.vite/
scripts/.run-logs/
scripts/data/local/
scripts/data/*.generated.json
scripts/data/*.local.json
Docker 持久化数据、.env、Python 缓存、测试缓存
```

## 相关文档

- [项目说明书](docs/项目说明书.md)：架构、配置、通道语义和维护边界；
- [统一智能问答设计](docs/spec/spec_20260915_144238_统一智能问答与通道解耦.md)；
- [统一智能问答任务](docs/task/task_20260915_144454_统一智能问答与通道解耦.md)；
- [多通道 RAG 设计](docs/spec/spec_20260915_125646_多通道RAG检索与图谱SQL问答.md)；
- [多通道 RAG 任务](docs/task/task_20260915_125646_多通道RAG检索与图谱SQL问答.md)；
- [文档切分策略设计](docs/spec/spec_20260915_202356_文档切分策略可选化.md)；
- [文档切分策略任务](docs/task/task_20260915_203753_文档切分策略可选化.md)；
- [RAG 评测说明](RAG-assessment/README.md)。

## 停止服务

```powershell
docker compose stop
```