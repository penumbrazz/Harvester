# Harvester

Harvester 是个人 home lab 信息采集控制平面。它提供公开网页抓取、raw evidence 保存、content item 抽取、去重、chunk 索引、关键词/向量搜索、审计和可部署基座。

## 技术栈

| 层         | 技术                                                  |
|-----------|-------------------------------------------------------|
| 后端 API   | Python 3.12+、FastAPI、SQLAlchemy 2、Alembic、Typer CLI |
| 前端控制台  | React + TypeScript + Vite（Animal Island UI 设计系统）  |
| 数据库     | PostgreSQL + pgvector                                  |
| 抓取适配器  | Firecrawl（自部署）、HTTP 直连                          |
| Embedding | Qwen（OpenAI-compatible）或 Stub（离线开发/CI）          |
| 依赖管理   | [uv](https://docs.astral.sh/uv/)（Python）、npm（前端） |
| 部署       | Docker Compose 或 `./start.sh` 本地启动                |

## 端口约定

| 服务            | 端口   |
|----------------|--------|
| Harvester API  | `8001` |
| 前端 Vite Dev  | `5173` |

---

## 快速部署

### 前置条件

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器
- Node.js ≥ 18、npm
- PostgreSQL（本地或 Docker）+ pgvector 扩展
- Firecrawl 服务（可选，自部署 `http://localhost:3002`）

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，至少填写以下关键配置：
```

| 环境变量                         | 说明                                       | 默认值                                     |
|--------------------------------|--------------------------------------------|--------------------------------------------|
| `HARVESTER_DATABASE_URL`       | PostgreSQL 连接字符串                       | `postgresql+psycopg://postgres:postgres@localhost:5432/harvester` |
| `HARVESTER_API_TOKEN`          | API 鉴权 Bearer Token                     | `change-me-in-production`                  |
| `HARVESTER_ARCHIVE_PATH`       | Raw payload 归档目录                       | `/data/harvester/archive`                  |
| `FIRECRAWL_API_URL`            | Firecrawl 服务地址                         | `http://localhost:3002`                    |
| `HARVESTER_EMBEDDING_ADAPTER`  | Embedding 适配器（`stub` 或 `qwen`）       | `stub`                                     |
| `HARVESTER_START_DAEMONS`      | `./start.sh` 是否同时启动 daemon 进程       | `0`（不启动）                               |

完整配置项参见 [.env.example](.env.example)。

### 2. 安装依赖

```bash
# 后端（Python）
uv sync --all-extras

# 前端
cd frontend && npm install && cd ..
```

### 3. 初始化数据库

```bash
uv run alembic upgrade head
```

### 4. 启动服务

#### 方式 A：一键启动（推荐）

```bash
# 只启动 API + 前端
./start.sh

# 启动 API + 前端 + 所有 daemon（scheduler、crawl worker、extract worker、embedding worker）
HARVESTER_START_DAEMONS=1 ./start.sh
```

启动后：
- 后端 API：`http://localhost:8001`
- 前端控制台：`http://localhost:5173`
- `Ctrl+C` 停止所有进程

#### 方式 B：Docker Compose

```bash
docker compose up -d
```

Docker Compose 包含以下服务：

| 服务           | 说明                    |
|---------------|-------------------------|
| `server`      | Harvester API（:8001）  |
| `worker`      | Embedding Worker Daemon |
| `scheduler`   | Scheduler Daemon        |
| `crawl-worker`| Crawl Worker Daemon     |

#### 方式 C：手动分别启动

```bash
# 后端 API
uv run uvicorn harvester.api.app:create_app --factory --host 0.0.0.0 --port 8001 --reload

# 前端
cd frontend && npm run dev

# Scheduler Daemon（按间隔扫描到期 schedule，创建 crawl job）
uv run harvester scheduler daemon

# Crawl Worker Daemon（消费 crawl job，执行网页抓取）
uv run harvester worker run --job-type crawl

# Extract Worker Daemon（消费 extract job，执行内容抽取）
uv run harvester worker run --job-type extract

# Embedding Worker Daemon（消费 embed_chunks job）
uv run harvester worker run --job-type embed_chunks
```

---

## 使用指南

### 核心概念

```
Source → Recipe → Schedule → CrawlRun → RawObject → Extraction → ContentItem → ItemVersion → Chunk → Search
```

| 概念           | 说明                                                  |
|---------------|-------------------------------------------------------|
| **Source**     | 抓取来源（一个网站或入口 URL），有状态机管理               |
| **Recipe**     | 抓取配方（如何抓取、抽取什么、发现规则），绑定到 Source     |
| **Schedule**   | 定时调度，按间隔自动触发抓取                             |
| **CrawlRun**   | 一次具体的抓取执行记录                                   |
| **RawObject**  | 抓取的原始 evidence（短保留，~7 天）                      |
| **ContentItem**| 从 raw data 抽取的最小内容单元（长期保留）                |
| **ItemVersion**| 内容版本（变更追踪）                                     |
| **Chunk**      | 搜索和 embedding 的输入单元                              |

### CLI 常用命令

所有 CLI 操作通过 `uv run harvester` 执行，状态变更通过 HTTP API 完成：

```bash
# ---- Source 管理 ----
uv run harvester source create --name "CDC 周报" --url "https://www.chinacdc.cn/jksj/jksj04_14249/"
uv run harvester source list
uv run harvester source promote --source-id <id>      # candidate → watched

# ---- Recipe 管理 ----
uv run harvester recipe create --source-id <id> --name "CDC 默认" --config '{...}'
uv run harvester recipe approve --recipe-id <id>       # pending → approved

# ---- 手动触发抓取 ----
uv run harvester crawl run --source-id <id> --recipe-id <id>

# ---- Schedule 管理 ----
uv run harvester schedule create --source-id <id> --recipe-id <id> --interval 3600
uv run harvester schedule list

# ---- 一次性运行 scheduler / worker ----
uv run harvester scheduler run                         # one-shot：扫描到期 schedule
uv run harvester worker once --job-type crawl --limit 10  # 处理 N 个 pending job

# ---- 队列状态 ----
uv run harvester queue status

# ---- 搜索 ----
uv run harvester search keyword --query "流感"
```

### API 使用

所有 API 需要 Bearer Token：

```bash
export TOKEN="your-token"

# 健康检查
curl http://localhost:8001/health

# 查看 Source 列表
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/sources

# 手动触发抓取
curl -X POST http://localhost:8001/crawl/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source_id": "...", "recipe_id": "..."}'

# 队列状态
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/queue/status

# 关键词搜索
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/search/keyword?query=流感"

# 查看失败记录
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/failures/recent

# 审计日志
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/audit/events
```

### 前端控制台

前端运行在 `http://localhost:5173`，提供可视化的 Source、Recipe、Schedule、CrawlRun、Queue 管理和搜索界面。

首次使用在 Overview 页面配置：
- **API Base URL**：`http://localhost:8001`
- **API Token**：对应环境变量 `HARVESTER_API_TOKEN` 的值

配置保存在浏览器 localStorage 中。

---

## 如何指挥 Code Agent 添加新抓取源

Harvester 项目内置了 agent 工作流，你可以用自然语言指挥 AI Code Agent（如 Gemini、Claude、Codex）添加新的抓取来源。Agent 会自动遵循项目规范完成接入。

### 工作原理

项目在 `.agent/skills/harvester-source-onboarding/SKILL.md` 中定义了完整的来源接入工作流。当你要求 agent 添加新来源时，agent 会：

1. **识别来源**：分析入口 URL、内容类型、content item 粒度
2. **复用优先搜索**：检查已有的 executor（`firecrawl`、`http_fetch`）和 extractor（CDC、Sina、PDF 等），优先复用
3. **选择接入方式**：仅配置 → 扩展现有 extractor → 新增 extractor
4. **TDD 实现**：先写测试，再写代码
5. **预览报告**：运行 dry-run 并展示抽取样例
6. **用户审批**：在你确认前，agent 不会 promote source 或创建正式 schedule

### 示例对话

以下是你可以直接发给 agent 的指令模板：

#### 示例 1：添加一个新闻列表页来源

```
帮我添加一个新的抓取来源：人民网国际新闻列表页
- 入口 URL：http://world.people.com.cn/
- 期望抽取每篇新闻的标题、链接、摘要
- 每 4 小时自动抓取一次
```

#### 示例 2：添加一个 RSS 源

```
添加一个 RSS 抓取来源：
- URL: https://example.com/feed.xml
- 抽取每篇文章的标题、正文、发布时间
- 每天抓取一次
```

#### 示例 3：添加一个有 PDF 资产的来源

```
我想抓取某机构的公开报告页面：
- 列表页 URL: https://example.org/reports/
- 列表页有详情链接，详情页有 PDF 下载
- 需要下载 PDF 并提取文本
- 参考已有的 CDC 周报 pipeline
```

#### 示例 4：只调整现有来源的配置

```
把 CDC 周报的抓取间隔从 1 小时改为 30 分钟，
同时把 discovery 的 max_targets_per_run 从 20 调到 50
```

### Agent 会执行的步骤

1. 阅读 `SKILL.md`、`AGENTS.md`、`README.md` 了解项目规范
2. 搜索 `harvester/extractors/` 和 `harvester/adapters/` 中的现有代码
3. 按复用优先规则选择最小变更方案
4. 编写/更新 fixture 测试（`tests/extractors/`、`tests/jobs/`）
5. 实现必要的代码变更
6. 运行测试确认通过
7. 提交预览报告，格式如下：

```
来源：XXX
入口 URL：https://...
接入方式：复用 firecrawl executor + 新增 xxx_extractor
复用判断：
- 复用 executor：是（firecrawl adapter 已支持 HTML 抓取）
- 复用 extractor：否（该站点 HTML 结构不同于现有 extractor）
- 新增代码范围：extractors/xxx.py + tests/extractors/test_xxx.py
抓取结果：成功获取 15 条新闻
抽取 content items：15
样例标题：《...》《...》
启用草案：
- source promote: 待确认
- recipe approve: 待确认
- schedule: 每 4 小时，待确认
```

8. **等你确认后**，agent 才会通过 CLI/API 执行 promote、approve 和创建 schedule

### 现有抓取能力一览

可直接复用的能力，无需新增代码：

| 能力               | 说明                                                  |
|-------------------|-------------------------------------------------------|
| Firecrawl Adapter | 通用公开网页抓取（HTML → Markdown 转换）                |
| HTTP 直连下载      | 直接 HTTP GET 下载二进制文件（如 PDF）                   |
| CDC 周报 Extractor | 中国 CDC 周报列表页 + 详情页解析                        |
| Sina 7x24 Extractor| 新浪财经 7x24 快讯流解析                                |
| PDF 文本 Extractor | PDF 文件文本提取                                       |
| Discovery Pipeline | 列表页 → 详情页 → PDF 资产的三级发现                    |
| Fetch Policy       | URL 安全校验（禁止内网、redirect 复检）                  |

### 添加新 Extractor 时的关键文件

```
harvester/extractors/
├── base.py              # Extractor Protocol 接口定义（CandidateItem、ExtractionOutput）
├── registry.py          # URL pattern → Extractor 映射注册
├── cdc_weekly.py        # 示例：CDC 周报 extractor
├── sina_7x24.py         # 示例：Sina 7x24 extractor
├── pdf_text.py          # 示例：PDF 文本 extractor
└── ...

tests/extractors/        # Extractor 单元测试
tests/jobs/              # Job handler / pipeline 测试
tests/integration/       # 集成测试
tests/fixtures/          # 测试 fixture 数据
```

新 extractor 只需实现 `Extractor` Protocol 的 `extract()` 方法，然后在 `registry.py` 中注册 URL pattern 即可。

---

## 运维参考

### 审计日志保留

- 默认保留 **7 天**（`HARVESTER_AUDIT_RETENTION_DAYS`）
- Scheduler daemon 自动按 24 小时间隔清理过期 audit events
- 清理不影响 source、recipe、job、content item 等业务数据

### Raw Payload 保留

- `raw_object` 是短保留 evidence cache，默认 ~7 天
- 提取成功后可压缩或删除 payload
- 长期保留的是 `content_item`、`item_version`、`chunk`

### Embedding 切换

```bash
# 默认：Stub（离线/CI，deterministic）
HARVESTER_EMBEDDING_ADAPTER=stub

# 切换到 Qwen（需要 OpenAI-compatible embedding 服务）
HARVESTER_EMBEDDING_ADAPTER=qwen
HARVESTER_EMBEDDING_MODEL=text-embedding-v3
HARVESTER_EMBEDDING_DIMENSION=1536
HARVESTER_QWEN_EMBEDDING_BASE_URL=http://localhost:8080
```

### Fetch Policy

- 只允许公开 `http`/`https` URL
- DNS 解析后拒绝 localhost、private IP、link-local 等
- Redirect 后复检 final URL
- 设有 timeout、最大响应大小、最大 redirect 次数
- 代理/VPN 环境可设置 `HARVESTER_FETCH_POLICY_SKIP_DNS=1` 跳过 DNS IP 检查

---

## 开发

### 运行测试

```bash
# 后端全量测试
uv run pytest -q

# 前端测试
cd frontend && npm test -- --run

# E2E 测试（需先启动 API + 前端）
cd frontend && npm run test:e2e
```

### 代码格式化

```bash
# Python
uv run ruff format . && uv run ruff check --fix .

# 前端
cd frontend && npm run format && npm run lint
```

### Live Smoke 测试

```bash
# 真实网络抓取
HARVESTER_ENABLE_LIVE_CRAWL=1 uv run pytest tests/integration/test_cdc_public_crawl_smoke.py -q

# CDC 专用
HARVESTER_CDC_LIVE_SMOKE=1 uv run pytest tests/jobs/test_cdc_live_smoke.py -v

# Qwen Embedding
HARVESTER_LIVE_QWEN_EMBEDDING=1 uv run pytest tests/integration/test_vector_search_api_pipeline.py -q
```

---

## 项目结构

```
Harvester/
├── harvester/              # 后端 Python 包
│   ├── api/                # FastAPI 路由、鉴权、依赖注入
│   │   └── routers/        # 各资源 API router
│   ├── cli/                # Typer CLI
│   ├── db/                 # SQLAlchemy models、session 管理
│   ├── domain/             # 领域逻辑（状态机、Fetch Policy、审计、URL 工具）
│   ├── extractors/         # 内容抽取器（Protocol + 注册表）
│   ├── adapters/           # 外部服务适配器（Firecrawl、Embedding）
│   ├── jobs/               # Job handler（crawl、extract、embed）
│   ├── workers/            # Worker daemon 实现
│   └── search/             # 关键词/向量搜索
├── frontend/               # React + TypeScript + Vite 前端
├── alembic/                # 数据库迁移
├── tests/                  # 测试（按模块分目录）
├── scripts/                # 运维脚本
├── .agent/skills/          # Agent 工作流技能定义
├── start.sh                # 一键启动脚本
├── docker-compose.yml      # Docker 部署配置
├── pyproject.toml          # Python 项目配置
└── .env.example            # 环境变量模板
```
