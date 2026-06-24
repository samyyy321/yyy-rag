# YYY-RAG

文档知识库与 RAG 问答系统，支持文档异步导入、知识库隔离检索、独立流式聊天界面和 TruLens 评测。

## 主要功能

- 知识库创建、查询、更新和删除；
- PDF、DOCX、TXT、Markdown 文档上传；
- MinerU / LlamaIndex 文档解析与异步导入；
- DashScope Embedding、Rerank 和 LLM；
- Milvus 向量检索与知识库隔离；
- SSE 流式 RAG 问答；
- React 前端：知识库管理、文档管理和独立聊天界面；
- PostgreSQL、MinIO、Milvus 健康检查；
- TruLens RAG 评测和 Dashboard。

## 技术栈

```text
FastAPI             后端 API 与 SSE 流式输出
React + Vite        前端工作台与独立聊天界面
TanStack Query      前端服务端状态管理
PostgreSQL          业务数据和导入任务
MinIO               原始文档存储
Milvus              向量存储和检索
DashScope           Embedding、Rerank、LLM
MinerU              可选文档解析服务
TruLens             RAG 评测
```

## 目录

```text
app/                React + Vite 前端
src/                FastAPI 应用源码
alembic/            数据库迁移
test/               后端测试
RAG-assessment/     TruLens 评测入口和评测集
docs/               设计文档、任务文档和项目说明书
docker-compose.yaml 本地依赖服务
requirements.txt    Python 依赖
.env.example        后端配置模板
```

## 快速启动

### 1. 激活后端环境

```powershell
conda activate yyy-rag
```

### 2. 准备后端配置

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，至少填写真实的：

```env
API_KEY=your-api-key
BASE_URL_CHAT=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.8-27b
EMBEDDING_MODEL=qwen3.7-text-embedding
RERANK_MODEL=qwen3.7-text-rerank
```

同时确认 PostgreSQL、MinIO 和 Milvus 配置正确。`.env` 不应提交到 Git。

### 3. 启动依赖服务

```powershell
docker compose up -d
```

### 4. 执行数据库迁移

```powershell
python -m alembic upgrade head
```

### 5. 启动后端 API

```powershell
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --reload
```

后端 Swagger 文档：

```text
http://127.0.0.1:8080/docs
```
### 6. 启动前端

另开一个终端，进入前端目录：

```powershell
cd app
npm install
npm run dev
```

首次运行需要执行 `npm install`。前端开发服务器会将 `/api` 请求代理到后端 API；如需调整代理目标，可复制 `app/.env.example` 为 `app/.env.local` 后修改 `VITE_DEV_API_TARGET`。

## API 总览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查 |
| POST / GET | `/api/v1/knowledge-bases` | 创建 / 列出知识库 |
| GET / PUT / DELETE | `/api/v1/knowledge-bases/{id}` | 查询 / 更新 / 删除知识库 |
| POST / GET | `/api/v1/knowledge-bases/{id}/documents` | 上传 / 列出文档 |
| GET / DELETE | `/api/v1/documents/{id}` | 查询 / 删除文档 |
| POST | `/api/v1/chat` | 非流式 RAG 问答，返回完整回答与来源 |
| POST | `/api/v1/chat/stream` | SSE 流式 RAG 问答，前端聊天界面使用 |

上传文档后返回 `202`，导入在后台执行。可通过以下接口查询导入状态：

```text
GET /api/v1/documents/{document_id}
```

`/api/v1/chat/stream` 使用与 `/api/v1/chat` 相同的 JSON 请求体，响应类型为 `text/event-stream`。每个事件包含一个文本片段：

```text
data: {"content":"一个回答片段"}
```

当离线索引没有可用页码时，RAG 内部引用会标注“页码未提供”；前端聊天界面不展示来源、页码或相似度。

## 测试

### 后端测试

```powershell
python -m compileall -q src test RAG-assessment
python -m pytest test/unit -q -p no:cacheprovider
python -m pytest test/evaluation -q -p no:cacheprovider
```

基础设施集成测试：

```powershell
$env:RUN_API_INTEGRATION = "1"
python -m pytest test/integration -q -p no:cacheprovider
```

### 前端测试与构建

```powershell
cd app
npm run test
npm run build
```

`npm run test` 使用模拟 API，不需要启动后端、数据库、对象存储、向量库或模型服务。`npm run build` 会执行 TypeScript 检查并生成生产构建。
## TruLens 评测

```powershell
$env:PYTHONPATH = (Get-Location).Path
$env:RUN_TRULENS_EVAL = "1"
$env:TRULENS_CASE_LIMIT = "1"
python RAG-assessment/run_trulens_evaluation.py
```

## 相关文档

- [项目说明书](docs/项目说明书.md)：架构、配置、数据模型和维护说明；
- [RAG 评测说明](RAG-assessment/README.md)；
- [后端设计文档](docs/spec/spec_20260911_160524_FastAPI文档知识库后端.md)；
- [前端设计文档](docs/spec/spec_20260914_193826_RAG知识库前端工作台.md)；
- [前端任务文档](docs/task/task_20260914_195611_RAG知识库前端工作台.md)。

## 停止服务

```powershell
docker compose stop
```