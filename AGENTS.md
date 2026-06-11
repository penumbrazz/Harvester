# AGENTS.md

总是用中文回复用户、编写文档及注释。

## 项目目标

Harvester 是个人 home lab 信息采集控制平面。第一版目标是公开网页抓取、raw evidence 保存、content item 抽取、去重、索引、搜索、审计和可部署基座。

## 端口约定

- **Harvester API（后端）**：`8001`（所有文档、脚本、配置统一使用此端口）
- **Frontend（Vite dev server）**：`5173`
- **omlx（LLM 服务）**：`8000`（外部服务，非 Harvester）

启动：`./start.sh`（同时启动前后端，Ctrl+C 停止）

## 工作方式

- 默认采用 Superpowers 工作流：涉及需求澄清、设计或行为变更时先使用 `superpowers:brainstorming`；实现前写清计划；调试问题时使用 `superpowers:systematic-debugging`；功能和 bugfix 采用 TDD；完成前使用 `superpowers:verification-before-completion` 做验证。
- 历史 `openspec/` 目录仅作为归档参考，不作为新开发的强制流程。不要再创建、安装或依赖项目本地 OpenSpec skill。
- 涉及前端视觉、布局、组件样式或交互状态时，必须先读根目录 `DESIGN.md`，并以其中的 Animal Island UI 风格设计系统为准。优先使用 `animal-island-ui` 提供的组件，参考 `AI_USAGE.md` 了解组件 API。
- 新增、修改、测试抓取来源，或用户说“爬一下”“抓一下”“单次抓取”“下载公开 PDF”时，必须先阅读并遵循 `.agent/skills/harvester-source-onboarding/SKILL.md`；优先复用现有 recipe、executor、extractor、pipeline 和测试结构，能复用就复用。
- 禁止用 `download_*.py`、`scrape_*.py`、本地 `*_pdfs/` 目录等独立脚本作为 Harvester 抓取任务的交付方案；临时探测可以存在，但最终必须迁移到 source、recipe、crawl run、raw_object、extractor、content item 流程。
- PDF、图片和附件类 raw evidence 必须按原文件格式保存到 Harvester archive 的类型化目录，保留可读原文件名；只有命名冲突时才追加短后缀，禁止统一保存成 `.raw` 或纯 UUID/hash 文件名。
- 单次抓取是正式运行模式，不等于 schedule。没有用户明确要求长期抓取时，不要创建 active schedule；应使用 Harvester API/CLI 的手动 crawl run 和 worker once 路径完成一次性抓取/抽取。
- 一次只实现一个明确目标，除非用户明确要求跨目标协作。
- 如果当前工作有 Superpowers spec、plan 或任务列表，任务完成后立刻更新对应状态。
- 采用 TDD。先写或更新测试，再实现，再运行相关测试。
- 不要绕过 Harvester API 直接写生产数据库。迁移和测试 fixture 例外。
- CLI 的状态变更必须通过 HTTP API，不直接创建数据库 session。
- 保持最小 diff，不做未纳入当前目标的顺手重构。
- 完成编码任务后，主动检查 `git status`。如果有未提交的更改，主动提议提交。提交后，主动提议使用 `code-reviewer` 和 `security-reviewer` 子代理进行代码审查。

## 核心架构约束

```text
raw_object 只回答：这次抓取看到了什么。
content_item / item_version / chunk 才是资料库和搜索层。
```

- `raw_object` 是短保留 evidence cache，不是长期语料库。
- 默认 raw HTML/API payload 可按约 7 天保留；提取成功后可压缩或删除 payload。
- 长期保留的是 metadata、hash、audit、`content_item`、`item_observation`、`item_version`、`chunk`。
- embedding 只能从 `item_version -> chunk` 开始，不能对 raw HTML/API payload 做 embedding。
- 瀑布流、时间线、搜索结果页不能整体当成一篇文档。必须抽取独立 `content_item`。
- 高频源必须用 frontier + rewind window + dedup，不能只依赖游标。
- pipeline stage 必须定义事务边界、唯一 upsert key 和下游 job 创建规则。



## 🧪 测试

**提交前务必运行测试。** 目标覆盖率：最低 40-60%。

**⚠️ Python 模块使用 [uv](https://docs.astral.sh/uv/) 管理依赖。始终使用 `uv run` 执行 Python 命令。**


**测试原则：**
- 遵循 AAA 模式：Arrange（准备）、Act（执行）、Assert（断言）
- Mock 外部服务（Anthropic、OpenAI、Docker、API）
- 测试边缘情况和错误条件
- 保持测试独立和隔离

**E2E 测试规则：**
- ⚠️ E2E 测试不允许优雅失败——禁止 `test.skip()`，禁止静默失败
- ⚠️ 前端禁止 Mock 后端 API——必须发送真实 HTTP 请求
- 如果测试失败，修复问题——绝不能为了通过 CI 而跳过

---

## 💻 代码风格

**⚠️ 所有代码注释必须使用英文编写。**

### 通用原则

- **高内聚，低耦合**：每个模块/类应有单一职责
- **文件大小限制**：如果文件超过 **1000 行**，应拆分为多个子模块
- **函数长度**：每个函数最多 50 行（推荐）

### 代码设计准则

⚠️ **实现新功能或修改现有代码时请遵循以下准则：**

1. **长期可维护性优于短期简洁性**：当存在多种实现方案时，避免那些现在实现简单但长期增加维护成本的方案。选择平衡实现成本和长期可持续性的方案。

2. **使用设计模式进行解耦**：积极考虑应用设计模式（如策略模式、工厂模式、观察者模式、适配器模式）来解耦模块并提高代码灵活性。这使代码库更易于扩展和测试。

3. **通过提取管理复杂性**：如果模块已经很复杂，优先将公共逻辑提取到工具模块或创建新模块，而不是在现有模块上增加更多复杂性。有疑问时，拆分而非扩展。

4. **先参考，再提取，然后复用**：实现新功能之前，务必：
   - 搜索解决类似问题的现有实现
   - 如有发现，从现有代码中提取可复用的模式
   - 创建可在代码库中复用的共享工具
   - 绝不复制粘贴代码或编写重复逻辑

5. **先重构再扩展**：分析代码时，识别与新功能相关的特性。如果存在相关代码，在添加新功能之前先使用设计模式重构并提取公共方法——绝不重新实现已有逻辑。

6. **修复所有发现的问题**：在开发过程中发现问题时，必须立即修复。绝不能因为问题看似"不相关"而忽略——发现的所有 bug 都必须处理。**主动审查**代码和文档中的问题——不要等待用户指出。

7. **优先采用行业标准而非项目惯例**：如果项目有不符行业标准的实践，应采用标准方法而非扩展非标准模式。这提高了代码的可维护性，减少了新开发者的上手难度。

8. **积极删除死代码**：无论需要多大努力，确保删除已废弃、未使用或过时的代码。死代码降低可维护性并造成混乱——保持代码库整洁是不可商量的。

9. **从所有代码中提取公共逻辑**：在进行更改时，如果发现应提取到共享工具的逻辑，立即执行。这适用于所有代码——不仅是"新代码复用旧代码"，也包括从现有代码段之间提取共性。每个复用机会都必须抓住。

10. **避免向后兼容——为理想状态设计**：实现更改时，就像没有遗留负担一样设计——考虑"如果从零开始，最好的方法是什么"。避免为旧逻辑编写兼容性垫片或变通方案。如果向后兼容绝对不可避免，在继续之前先与用户协商。

### Python（Backend、Executor、Shared）

**标准：** PEP 8、Ruff 格式化（行长度：88）、必须使用类型提示

```bash
uv run ruff format . && uv run ruff check --fix .
```

**准则：**
- 使用描述性命名，公共函数/类必须有 docstring
- 将魔法数字提取为常量

### TypeScript/React（Frontend）

**标准：** TypeScript 严格模式、函数式组件、Prettier、ESLint、单引号、无分号

```bash
npm run format && npm run lint
```

**准则：**
- 优先使用 `const` 而非 `let`，禁止使用 `var`
- 组件名：PascalCase，文件名：kebab-case
- 类型定义放在 `src/types/`

### 组件复用

⚠️ **创建新组件前务必检查现有组件**

1. 优先检查 `animal-island-ui` 提供的组件（Button、Card、Input、Select、Modal、Switch、Tabs、Checkbox、Collapse 等）
2. 在 `src/components/ui/`、`src/components/common/`、`src/features/*/components/` 中搜索现有组件
3. 如果多次实现类似的 UI 模式，提取可复用逻辑

### 测试属性（data-testid）

⚠️ **保留并添加 `data-testid` 属性用于 E2E 测试**

**修改现有代码时：**
- ✅ **始终保留**现有的 `data-testid` 属性——它们被 E2E 测试使用
- ❌ 不要重命名或删除 `data-testid`，除非同时更新对应的 E2E 测试

**创建新的交互组件时：**
- ✅ **必须添加** `data-testid` 属性到交互元素（按钮、输入框、链接、选择框等）
- ✅ 使用描述性的、一致的命名：`{动作}-{元素类型}`（例如 `save-button`、`cancel-link`、`search-input`）
- ❌ 不要在交互元素上省略 `data-testid`

---

## 🔄 Git 工作流

### 分支命名与提交

**分支模式：** `<类型>/<描述>`（feature/、fix/、refactor/、docs/、test/、chore/）

**提交格式：** [约定式提交](https://www.conventionalcommits.org/)
```
<type>[scope]: <description>
# 类型：feat | fix | docs | style | refactor | test | chore
# 示例：feat(backend): add Ghost YAML import API
```

### Git 钩子

目前项目未配置自动 git hooks。提交前请手动运行格式化和测试：

```bash
# Backend
uv run ruff format . && uv run ruff check --fix .
uv run pytest tests/ -q

# Frontend
cd frontend && npm run format && npm run lint && npm test -- --run
```


---
