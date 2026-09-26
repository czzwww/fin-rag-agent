# 财报/公告结构化问答 Agent

> 面向金融财报场景的**双通道**问答系统：研报文本 RAG + 财务数值结构化推理，支持引用溯源与库外拒答。

## 为什么做这个

通用知识库产品（Ima / NotebookLM）对财报**表格数值**易失真、无法计算、不可溯源。本项目从 0 到 1 构建可部署的双通道问答系统：

- **表格不失真**：`pdfplumber` 单独抽取表格并保留结构
- **数值用工具算**：pandas 计算 CAGR/YoY/比率，杜绝算术幻觉
- **可溯源到页码**：答案标注 `[来源:文件名 P页码]`
- **可被脚本/服务调用**：FastAPI 暴露 HTTP 接口

## 架构

```
用户问题（自然语言）
        │
┌───────▼────────┐
│ LangGraph 路由  │  数值 / 文本 / 混合
└───┬────────┬───┘
    │        │
    ▼        ▼
 数值通道   文本通道（RAG）
 SQLite      FAISS 向量 + BM25
 + pandas    + RRF 融合 + 重排
    └───┬────┘
        ▼
   verify 自检 ──不通过──► 重检索/重算
        ▼
 答案 + 数值 + 引用[来源:页码]
```

## 核心特性

| 能力 | 说明 |
|------|------|
| 财报表格解析 | pdfplumber 抽取正文 + 表格，保留页码与表号 |
| 结构化抽取 | LLM 将财务指标抽取为归一化 schema，入 SQLite |
| 双通道检索 | 文本走混合检索，数值走指标库 |
| 数值工具推理 | CAGR / YoY / ratio 用 pandas 计算 |
| 意图路由 | LangGraph 路由数值 / 文本 / 混合，含自检循环 |
| 引用溯源 + 拒答 | 答案标注来源页码，库外问题拒绝回答 |
| 增量入库 | 哈希去重、FAISS 追加、版本化、一键重建 |
| 评测体系 | 命中率、拒答率、平均耗时 |

## 技术栈

Python 3.11 · uv · DeepSeek（OpenAI 兼容）· 智谱 embedding-2 · LangGraph · FastAPI · pdfplumber · faiss-cpu · rank_bm25 · jieba · pandas · SQLite · AKShare · Docker

## 目录结构

```
fin-rag-agent/
├── app/
│   ├── config.py        # 配置
│   ├── embedding.py     # 可插拔 embedding（智谱 / 本地 BGE）
│   ├── store.py         # FAISS + SQLite + 入库档案
│   ├── ingest.py        # 解析 + 切分 + 向量化 + 抽取
│   ├── extract.py       # LLM 结构化抽取
│   ├── retriever.py     # BM25 + 向量混合检索 + 重排
│   ├── rag.py           # 引用溯源 + 阈值拒答
│   ├── tools/           # query_metrics / compute + MCP 声明
│   ├── agent.py         # LangGraph 编排
│   ├── api.py           # FastAPI 接口
│   └── eval.py          # 评测
├── scripts/
│   └── download_reports.py   # 巨潮资讯财报下载
├── data/reports/        # 财报 PDF（不纳入版本控制）
├── storage/             # faiss.index + id_map.json + metrics.db
├── main.py
├── Dockerfile
└── docker-compose.yml
```

## 快速开始

```bash
# 1. 安装依赖
uv sync

# 2. 配置 .env（见下）
cp .env.example .env

# 3. 准备财报 PDF 到 data/reports/，然后入库
uv run python -m app.ingest

# 4. 启动服务
uv run python main.py
# 打开 http://localhost:8000/docs
```

### 环境变量（`.env`）

```env
OPENAI_API_KEY=你的DeepSeekKey
OPENAI_BASE_URL=https://api.deepseek.com
ZHIPU_API_KEY=你的智谱Key
EMBED_PROVIDER=zhipu
EMBED_MODEL=embedding-2
```

## API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/ask` | POST | 问答，返回 `answer` + `citations` + `metrics` |
| `/metrics` | GET | 查询结构化指标 |

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "贵州茅台2023年营业收入是多少？"}'
```

## 评测

```bash
uv run python -m app.eval    # 结果写入 metrics.json
```

当前结果：

| 指标 | 结果 |
|------|------|
| 数值题命中率 | 1/1 |
| 文本题命中率 | 1/1 |
| 拒答题正确率 | 2/2 |
| 平均耗时 | 2.57 s |

## Docker 部署

```bash
uv export --format requirements-txt -o requirements.txt
docker compose up --build
```

> `.env`、`storage/`、`data/` 通过运行时注入/挂载，不打进镜像（由 `.dockerignore` 保证）。

## 注意事项

- 智谱 `embedding-2` 单次 `input` ≤ 64 条，且不支持 openai SDK 注入的 `encoding_format` 字段，本项目用 `requests` 直连规避。
- 更换 embedding 模型后需全量重建向量库：`uv run python -m app.ingest --rebuild`。

## 免责声明

本项目仅用于技术学习与研究，所有财务数据来源于公开披露文件，不构成任何投资建议。
