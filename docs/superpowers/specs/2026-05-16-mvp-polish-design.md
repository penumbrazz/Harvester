# Harvester MVP 打磨方案

日期：2026-05-16
状态：草稿

## 目标

在新功能（LightRAG/KG/MCP、fetch policy、auth profile）启动之前，打磨和稳固 MVP。聚焦于测试覆盖、代码质量、缺陷修复、UX 改善和文档完善。

## 阶段划分

五个顺序阶段，每个阶段产出一个可提交的成果。

---

## 阶段 1：测试修复与覆盖率基线

### 1.1 跑全部测试，修复失败项

- 运行后端全部测试（`uv run pytest tests/`）
- 运行前端单元测试（`npm test`）
- 运行前端 E2E 测试（Playwright 连接真实后端）
- 记录并修复所有失败；不允许 skip 或静默失败

### 1.2 测量覆盖率基线

- 生成后端覆盖率报告（`uv run pytest --cov=harvester`）
- 识别覆盖率低于 40% 的模块
- 记录基线数据用于跟踪

### 1.3 补充缺失的后端 API 测试

**Sources**（扩展 `tests/api/test_sources.py`）：
- PATCH /sources/{id} — 编辑 name、URL、trust_level；验证 audit event

**Recipes**（在 `tests/api/test_recipes.py` 中新增用例）：
- POST /recipes/{id}/reject — pending->rejected，验证状态 + 审计
- POST /recipes/{id}/resubmit — rejected->pending，验证状态 + 审计
- POST /recipes/{id}/deprecate — approved->deprecated，验证状态 + 审计
- PATCH /recipes/{id} — 编辑 name、config；验证审计
- 非法转换：reject 已 approve 的 recipe、resubmit 非 rejected 的、deprecate pending 的

**Schedules**（在 `tests/api/test_watch_schedules.py` 中新增用例）：
- POST /schedules/{id}/pause — active->paused，验证状态 + 审计
- POST /schedules/{id}/resume — paused->active，验证状态 + 审计
- POST /schedules/{id}/disable — active/paused->disabled，验证状态 + 审计
- PATCH /schedules/{id} — 编辑 interval_seconds，验证审计
- 非法转换：pause 已暂停的、resume 非暂停的、disable 已禁用的

### 1.4 补充缺失的前端 E2E 测试

**Content 页面**（新建 `frontend/e2e/content-library.spec.ts`）：
- 导航到 content 页面
- 列出 content items，验证表格渲染
- 按 source、item_type、status 筛选
- 关键词搜索并验证结果
- 向量搜索并验证结果（或 adapter 不可用时 503）
- 无内容时的空状态

**Source Resume**（扩展 `frontend/e2e/source-management.spec.ts`）：
- Resume 暂停的 source，验证状态变化

### 1.5 验收标准

- 所有测试绿色通过（后端 + 前端单元 + E2E）
- 覆盖率基线已记录
- 没有 API 端点缺少测试
- 每个实体的状态转换都有后端 API 测试覆盖

---

## 阶段 2：端到端实际抓取 Smoke 测试

### 2.1 新浪 7x24 实际抓取 smoke 测试

新建文件：`tests/integration/test_sina_7x24_live_crawl_smoke.py`

- 标记 `@pytest.mark.live`，需要 `HARVESTER_ENABLE_LIVE_CRAWL=1`
- 调用真实 Firecrawl adapter 抓取新浪 7x24 页面
- 用 Sina7x24Extractor 处理真实 HTML
- 验证：content_item 创建、item_version 有内容、observations 关联正确
- 验证：关键词搜索能找到提取的内容

### 2.2 CDC Weekly 实际抓取 smoke 测试

`test_cdc_public_crawl_smoke.py` 中已有部分覆盖。扩展或新建：
- 通过 Firecrawl 抓取真实 CDC weekly 页面
- 用 CDCWeeklyExtractor 处理真实 HTML
- 验证完整 pipeline：raw_object -> content_item -> item_version -> 关键词可搜索

### 2.3 完整工作流 smoke 测试

新建文件：`tests/integration/test_full_workflow_smoke.py`

- 标记 `@pytest.mark.live`
- 通过 API 执行完整生命周期：
  1. 提议 source（新浪或 CDC）
  2. 提升 source 为 watched
  3. 创建 recipe
  4. 批准 recipe
  5. 通过 POST /crawl/run 触发抓取
  6. 等待抓取完成（轮询 + 超时）
  7. 验证 raw_objects 存在
  8. 验证 content_items 已提取
  9. 搜索并验证结果可找到
  10. 验证审计记录包含关键转换

### 2.4 验收标准

- Live smoke 测试通过真实后端 + 真实外部源
- 非 live 测试不受影响
- Smoke 测试为 opt-in（环境变量门控），不纳入日常 CI

---

## 阶段 3：缺陷修复与 UX 打磨

### 3.1 缺陷清单

- 收集阶段 1-2 测试中发现的缺陷
- 审计 API 错误处理一致性（是否所有错误都返回 JSON 格式含 detail 字段）
- 检查前端边界情况：
  - 所有列表页的空状态
  - API 调用时的加载状态
  - API 失败时的错误提示
  - 表单校验（必填字段、格式检查）

### 3.2 API 错误处理

- 确保所有 4xx/5xx 响应格式一致：`{"detail": "..."}`
- 验证状态机转换错误返回 400 并附带清晰信息
- 验证 not-found 返回 404（而非 500）

### 3.3 前端 UX

- 空状态组件：content 列表、审计日志、jobs、crawls
- 数据加载时的加载指示器/骨架屏
- 错误边界 / API 失败时的错误提示
- 表单验证反馈（必填字段、无效输入）

### 3.4 验收标准

- 正常工作流中无未处理错误
- 所有列表页展示有意义的空状态
- 所有表单提交前进行验证
- API 错误展示用户友好的信息

---

## 阶段 4：代码质量清理

### 4.1 死代码清理

- 查找并移除未使用的 import（`ruff check --select F401`）
- 查找并移除未使用的函数/类（交叉引用 grep）
- 移除注释掉的代码块

### 4.2 提取重复逻辑

- 扫描跨文件的重复模式
- 3 处以上重复时提取为共享工具
- 检查 extractors 是否有可提取的公共基类模式

### 4.3 文件大小审计

- 列出超过 500 行的文件，评估是否需要拆分
- 优先级：超过 1000 行的文件必须拆分

### 4.4 类型提示与代码风格

- 确保所有公共函数有类型提示
- 运行 `black . && isort .`（后端）
- 运行 `npm run format && npm run lint`（前端）
- 修复所有 lint 警告

### 4.5 验收标准

- 没有超过 1000 行的文件
- 没有 lint 错误（后端 + 前端）
- 没有死代码（未使用的 import、不可达代码）
- 重复逻辑已提取为共享工具

---

## 阶段 5：文档完善

### 5.1 更新 README

- 验证 README 与当前 API 端点一致
- 更新架构图（如需要）
- 验证安装说明准确（端口、环境变量、命令）

### 5.2 API 文档

- 验证 OpenAPI schema 完整（FastAPI 自动生成）
- 为端点 docstring 添加描述和示例
- 确保所有请求/响应 schema 有描述

### 5.3 项目约定审查

- 审查 CLAUDE.md / AGENTS.md：约定是否仍然准确
- 审查 DESIGN.md：前端是否仍符合设计系统
- 更新 TODOS.md（如果优先级有变化）

### 5.4 验收标准

- README 准确反映当前状态
- 所有 API 端点有含描述的 docstring
- 项目约定文档保持最新

---

## 不在范围内

- 新 extractor（RSS、微博、微信公众号）
- LightRAG / KG / MCP 集成
- Fetch policy（URL 安全边界）
- Auth profile / sandbox
- 新 CLI 命令
- 性能优化
- 登录/认证系统
