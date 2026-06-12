# YYY-RAG

文档知识库与 RAG 问答后端，支持文档异步导入、知识库隔离检索、来源返回和 TruLens 评测。

## 主要功能

- 知识库 CRUD；
- PDF、DOCX、TXT、Markdown 文档上传；
- MinerU / LlamaIndex 文档解析；
- DashScope Embedding 和 LLM；
- Milvus 向量检索与重排；
- 文档来源返回；
- PostgreSQL、MinIO、Milvus 健康检查；
- TruLens RAG 评测和 Dashboard。

## 技术栈

```text
FastAPI       API 服务
PostgreSQL    业务数据和导入任务
MinIO         原始文档存储
Milvus        向量存储和检索
DashScope     Embedding、Rerank、LLM
MinerU        可选文档解析服务
TruLens       RAG 评测
```

## 目录

```text
src/                 应用源码
alembic/             数据库迁移
test/                测试
RAG-assessment/      TruLens 评测入口和评测集
docs/                设计文档和项目说明书
docker-compose.yaml  本地依赖服务
requirements.txt     Python 依赖
.env.example         配置模板
```

## 快速启动

### 1. 激活环境

```powershell
conda activate yyy-rag
```

### 2. 准备配置

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

### 5. 启动 API

```powershell
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --reload
```

Swagger 地址：

```text
http://127.0.0.1:8080/docs
```

## API 总览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查 |
| POST / GET | `/api/v1/knowledge-bases` | 创建 / 列出知识库 |
| GET / PUT / DELETE | `/api/v1/knowledge-bases/{id}` | 查询 / 更新 / 删除知识库 |
| POST / GET | `/api/v1/knowledge-bases/{id}/documents` | 上传 / 列出文档 |
| GET / DELETE | `/api/v1/documents/{id}` | 查询 / 删除文档 |
| POST | `/api/v1/chat` | RAG 问答 |

上传文档后返回 `202`，导入在后台执行。通过以下接口查询导入状态：

```text
GET /api/v1/documents/{document_id}
```

## 测试

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
- [后端设计文档](docs/spec/spec_20260911_160524_FastAPI文档知识库后端.md)。

## 停止服务

```powershell
docker compose stop
```
